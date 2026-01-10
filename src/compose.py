"""Article composition module - creates unified article from summaries"""

import logging
from pathlib import Path
from typing import Dict, List

from src.summarize import LLMClient
from src.utils.text_formatting import normalize_markdown_structure
from .prompts import load_prompt, render_prompt

logger = logging.getLogger(__name__)


def compose_article(summaries: List[Dict[str, any]], provider: str = "openai") -> str:
    """Compose a unified article from multiple summaries

    Args:
        summaries: List of summary dictionaries with 'title', 'url', 'summary'
        provider: LLM provider ('openai' or 'anthropic')

    Returns:
        Markdown-formatted article (1200-1600 characters)
    """
    llm_client = LLMClient(provider=provider)

    # Build prompt with all summaries
    summaries_text = ""
    for i, summary in enumerate(summaries, 1):
        summaries_text += f"\n### 記事{i}: {summary['title']}\n"
        summaries_text += f"出典: {summary['url']}\n"
        summaries_text += "要点:\n"
        for point in summary['summary']:
            summaries_text += f"- {point}\n"

    system_prompt = load_prompt("compose/system")
    user_template = load_prompt("compose/user")
    user_prompt = render_prompt(user_template, summaries=summaries_text)

    try:
        logger.info("Composing unified article from summaries")
        # Some models (e.g., certain Mini tiers) do not allow non-default temperature.
        article = llm_client.generate(system_prompt, user_prompt, temperature=None)

        article = normalize_markdown_structure(article)

        # Validate article length
        char_count = len(article)
        logger.info(f"Article composed: {char_count} characters")

        if char_count < 800:
            logger.warning(f"Article is shorter than expected: {char_count} chars")

        return article

    except Exception as e:
        logger.error(f"Failed to compose article: {e}")
        raise


def save_draft(article: str, output_file: str = "draft.md"):
    """Save article to markdown file

    Args:
        article: Markdown article text
        output_file: Output file path
    """
    try:
        output_path = Path(output_file)
        parent_dir = output_path.parent
        if parent_dir and parent_dir != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open('w', encoding='utf-8') as f:
            f.write(article)
        logger.info(f"Draft saved to {output_file}")
    except IOError as e:
        logger.error(f"Failed to save draft: {e}")
        raise
