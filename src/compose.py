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
        article = _insert_series_links(article)

        # Validate article length
        char_count = len(article)
        logger.info(f"Article composed: {char_count} characters")

        if char_count < 800:
            logger.warning(f"Article is shorter than expected: {char_count} chars")

        return article

    except Exception as e:
        logger.error(f"Failed to compose article: {e}")
        raise


def _insert_series_links(article: str) -> str:
    url_a = os.getenv("SERIES_LINK_A")
    url_b = os.getenv("SERIES_LINK_B")
    if not url_a and not url_b:
        return article

    label_a = os.getenv("SERIES_LINK_A_LABEL", "すぐ使う：速報本文テンプレ")
    label_b = os.getenv("SERIES_LINK_B_LABEL", "設定・計測：はてなブログ向け設定")

    block_lines = ["> 次に読む"]
    if url_a:
        block_lines.append(f"> - {label_a}：{url_a}")
    if url_b:
        block_lines.append(f"> - {label_b}：{url_b}")
    block_lines.append("")

    lines = article.splitlines()
    intro_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("## 導入"):
            intro_idx = idx
            break
    if intro_idx is None:
        return article

    i = intro_idx + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and lines[i].strip():
        i += 1
    insert_at = i if i <= len(lines) else len(lines)

    lines[insert_at:insert_at] = [""] + block_lines
    return "\n".join(lines)


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
