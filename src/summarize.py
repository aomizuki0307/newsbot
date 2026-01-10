"""Article summarization module using LLMs"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from anthropic import Anthropic
from openai import OpenAI

from .prompts import load_prompt, render_prompt
from .utils.retry import llm_retry

logger = logging.getLogger(__name__)

SUMMARY_CONCURRENCY = 5


@dataclass
class SummarizationResult:
    """Container for summarize_articles outputs."""

    summaries: List[Dict[str, Any]]
    failed: int
    estimated_tokens: int
    skipped_due_to_budget: int = 0

    @property
    def limit_reached(self) -> bool:
        return self.skipped_due_to_budget > 0


class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic"""

    def __init__(self, provider: str = "openai"):
        self.provider = provider.lower()

        if self.provider == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @llm_retry()
    def generate(self, system: str, user: str, temperature: Optional[float] = None) -> str:
        """Generate text using the configured LLM

        Args:
            system: System prompt
            user: User prompt
            temperature: Sampling temperature (None = API default)

        Returns:
            Generated text
        """
        try:
            if self.provider == "openai":
                kwargs = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                }
                if temperature is not None:
                    kwargs["temperature"] = temperature
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content

            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    system=system,
                    messages=[
                        {"role": "user", "content": user}
                    ],
                    temperature=temperature if temperature is not None else 0.7,
                    max_tokens=2048
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise


def summarize_article(article: Dict[str, str], llm_client: LLMClient) -> Dict[str, Any]:
    """Summarize a single article into 5 key points in Japanese."""
    max_points = _summary_max_points()
    system_prompt = load_prompt("summarize/system")
    user_template = load_prompt("summarize/user")
    truncated_body = (article.get("text") or "")[:3000]
    user_prompt = render_prompt(
        user_template,
        title=article.get("title", ""),
        body=truncated_body,
    )

    try:
        response = llm_client.generate(system_prompt, user_prompt)

        # Parse bullet points
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        summary_points = []

        for line in lines:
            # Remove bullet markers (-, *, 1., etc.)
            cleaned = line.lstrip('-*•').lstrip('0123456789.').strip()
            if cleaned and len(cleaned) > 10:
                summary_points.append(cleaned)

        # Enforce a configurable upper bound
        summary_points = summary_points[:max_points]

        if len(summary_points) < 3:
            logger.warning(f"Only {len(summary_points)} points extracted, using raw response")
            summary_points = [response]

        return {
            'title': article['title'],
            'url': article['url'],
            'summary': summary_points
        }

    except Exception as e:
        logger.error(f"Failed to summarize article {article['url']}: {e}")
        raise


def _summary_max_points() -> int:
    """Return max summary points from env or default."""
    raw = os.getenv("SUMMARY_MAX_POINTS", "").strip()
    if not raw:
        return 8
    try:
        parsed = int(raw)
    except ValueError:
        return 8
    return parsed if parsed > 0 else 8


def summarize_articles(
    articles: List[Dict[str, str]],
    provider: str = "openai",
    max_tokens: Optional[int] = None,
) -> SummarizationResult:
    """Summarize multiple articles with concurrency and token budgeting."""

    executor = ThreadPoolExecutor(max_workers=SUMMARY_CONCURRENCY)

    async def _run(executor: ThreadPoolExecutor) -> SummarizationResult:
        semaphore = asyncio.Semaphore(SUMMARY_CONCURRENCY)
        llm_client = LLMClient(provider=provider)
        scheduled_tasks = []
        budget_used = 0
        total_failed = 0
        skipped_due_to_budget = 0
        loop = asyncio.get_running_loop()

        async def _summarize_with_limit(index: int, article: Dict[str, str]):
            nonlocal total_failed
            async with semaphore:
                try:
                    logger.info(
                        "Summarizing article %s/%s: %s",
                        index,
                        len(articles),
                        article.get("title", "")[:50],
                    )
                    return await loop.run_in_executor(
                        executor,
                        summarize_article,
                        article,
                        llm_client,
                    )
                except Exception as exc:
                    total_failed += 1
                    logger.error(
                        "Skipping article %s due to summarization error: %s",
                        article.get("url"),
                        exc,
                    )
                    return None

        for i, article in enumerate(articles, 1):
            estimated = _estimate_tokens_for_article(article.get("text", ""))
            if max_tokens and (budget_used + estimated) > max_tokens:
                skipped_due_to_budget = len(articles) - (i - 1)
                logger.warning(
                    "Token budget (%s) would be exceeded. Skipping remaining %s articles.",
                    max_tokens,
                    skipped_due_to_budget,
                )
                break

            budget_used += estimated
            scheduled_tasks.append(_summarize_with_limit(i, article))

        summaries: List[Dict[str, Any]] = []
        if scheduled_tasks:
            results = await asyncio.gather(*scheduled_tasks, return_exceptions=False)
            summaries = [result for result in results if result]

        logger.info(
            "Successfully summarized %s/%s articles (failed=%s, skipped=%s)",
            len(summaries),
            len(articles),
            total_failed,
            skipped_due_to_budget,
        )

        return SummarizationResult(
            summaries=summaries,
            failed=total_failed,
            estimated_tokens=budget_used,
            skipped_due_to_budget=skipped_due_to_budget,
        )

    try:
        return asyncio.run(_run(executor))
    finally:
        executor.shutdown(wait=True, cancel_futures=False)


def _estimate_tokens_for_article(text: str) -> int:
    """Rudimentary token estimate (~4 characters per token + response overhead)."""
    if not text:
        return 100
    return max(100, len(text) // 4 + 200)
