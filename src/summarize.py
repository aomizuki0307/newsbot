"""Article summarization module using LLMs"""

import logging
import os
from typing import Dict, List

from anthropic import Anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)


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


def summarize_article(article: Dict[str, str], llm_client: LLMClient) -> Dict[str, any]:
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


def summarize_articles(articles: List[Dict[str, str]], provider: str = "openai") -> List[Dict[str, any]]:
    """Summarize multiple articles

    Args:
        articles: List of article dictionaries
        provider: LLM provider ('openai' or 'anthropic')

    Returns:
        List of summary dictionaries
    """
    llm_client = LLMClient(provider=provider)
    summaries = []

    for i, article in enumerate(articles, 1):
        try:
            logger.info(f"Summarizing article {i}/{len(articles)}: {article['title'][:50]}")
            summary = summarize_article(article, llm_client)
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Skipping article due to summarization error: {e}")

    logger.info(f"Successfully summarized {len(summaries)}/{len(articles)} articles")
    return summaries
