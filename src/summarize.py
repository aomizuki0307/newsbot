"""Article summarization module using LLMs"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from anthropic import Anthropic
from openai import OpenAI

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
    def generate(self, system: str, user: str, temperature: float = 0.7) -> str:
        """Generate text using the configured LLM

        Args:
            system: System prompt
            user: User prompt
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content

            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    system=system,
                    messages=[
                        {"role": "user", "content": user}
                    ],
                    temperature=temperature,
                    max_tokens=2048
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise


def summarize_article(article: Dict[str, str], llm_client: LLMClient) -> Dict[str, Any]:
    """Summarize a single article into 5 key points in Japanese

    Args:
        article: Article dictionary with 'title', 'text', 'url'
        llm_client: LLM client instance

    Returns:
        Dictionary with 'title', 'url', 'summary' (list of 5 points)
    """
    system_prompt = """あなたは日本語テックメディアの編集アシスタントです。
技術記事を正確に要約し、重要なポイントを箇条書きで抽出します。
事実に基づき、専門用語は適切に使用してください。"""

    user_prompt = f"""以下の記事を日本語で5つの要点に要約してください。
各要点は1文で簡潔に。数値、日付、固有名詞は正確に記載してください。

タイトル: {article['title']}
本文:
{article['text'][:3000]}

要約（5つの要点を箇条書きで）:"""

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

        # Ensure we have exactly 5 points
        summary_points = summary_points[:5]

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


def summarize_articles(
    articles: List[Dict[str, str]],
    provider: str = "openai",
    max_tokens: Optional[int] = None,
) -> SummarizationResult:
    """Summarize multiple articles with concurrency and token budgeting."""

    async def _run() -> SummarizationResult:
        semaphore = asyncio.Semaphore(SUMMARY_CONCURRENCY)
        llm_client = LLMClient(provider=provider)
        scheduled_tasks = []
        budget_used = 0
        total_failed = 0
        skipped_due_to_budget = 0
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=SUMMARY_CONCURRENCY)

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

        try:
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
        finally:
            executor.shutdown(wait=True, cancel_futures=False)

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

    return asyncio.run(_run())


def _estimate_tokens_for_article(text: str) -> int:
    """Rudimentary token estimate (~4 characters per token + response overhead)."""
    if not text:
        return 100
    return max(100, len(text) // 4 + 200)
