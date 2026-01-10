"""Article composition module - creates unified article from summaries"""

import logging
import os
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

    plan_text = ""
    if _should_enable_stage("PLAN_ENABLED"):
        plan_text = _build_plan(summaries, summaries_text, llm_client)

    system_prompt = load_prompt("compose/system")
    user_template = load_prompt("compose/user")
    user_prompt = render_prompt(
        user_template,
        summaries=summaries_text,
        plan=plan_text or "（未実行）",
        revenue_model=_env_or_default("REVENUE_MODEL", "AdSense"),
        primary_query=_env_or_default("PRIMARY_QUERY", "未指定"),
        related_queries=_env_or_default("RELATED_QUERIES", "未指定"),
        funnel_stage=_env_or_default("FUNNEL_STAGE", "未指定"),
        target_reader=_env_or_default("TARGET_READER", "未指定"),
        goal_action=_env_or_default("GOAL_ACTION", "未指定"),
        pr_disclosure=_env_or_default("PR_DISCLOSURE", "無"),
        first_party_info=_env_or_default("FIRST_PARTY_INFO", "未指定"),
        existing_urls=_env_or_default("EXISTING_URLS", "未指定"),
        affiliate_categories=_env_or_default("AFFILIATE_CATEGORIES", "未指定"),
        title_hint=_env_or_default("TITLE_HINT", "未指定"),
    )

    try:
        logger.info("Composing unified article from summaries")
        # Some models (e.g., certain Mini tiers) do not allow non-default temperature.
        article = llm_client.generate(system_prompt, user_prompt, temperature=None)

        article = normalize_markdown_structure(article)
        article = _insert_series_links(article)

        _run_final_check(article, llm_client)

        # Validate article length
        char_count = len(article)
        logger.info(f"Article composed: {char_count} characters")

        if char_count < 800:
            logger.warning(f"Article is shorter than expected: {char_count} chars")

        return article

    except Exception as e:
        logger.error(f"Failed to compose article: {e}")
        raise


def _env_or_default(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _should_enable_stage(env_name: str) -> bool:
    raw = os.getenv(env_name)
    if raw is None:
        return os.getenv("PROMPT_VARIANT", "default").strip().lower() == "seo"
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _build_plan(
    summaries: List[Dict[str, any]],
    summaries_text: str,
    llm_client: LLMClient,
) -> str:
    theme_candidates = "\n".join(
        f"- {summary['title']}" for summary in summaries if summary.get("title")
    )
    plan_system = load_prompt("plan/system")
    plan_user = load_prompt("plan/user")
    plan_prompt = render_prompt(
        plan_user,
        revenue_model=_env_or_default("REVENUE_MODEL", "AdSense"),
        theme_candidates=theme_candidates or "（なし）",
        target_reader=_env_or_default("TARGET_READER", "未指定"),
        first_party_info=_env_or_default("FIRST_PARTY_INFO", "未指定"),
        existing_urls=_env_or_default("EXISTING_URLS", "未指定"),
        affiliate_categories=_env_or_default("AFFILIATE_CATEGORIES", "未指定"),
        summaries=summaries_text,
    )
    logger.info("Planning article outline and revenue flow")
    return llm_client.generate(plan_system, plan_prompt, temperature=None)


def _run_final_check(article: str, llm_client: LLMClient) -> None:
    if not _should_enable_stage("FINAL_CHECK_ENABLED"):
        return
    review_system = load_prompt("review/system")
    review_user = load_prompt("review/user")
    review_prompt = render_prompt(
        review_user,
        article=article,
        primary_query=_env_or_default("PRIMARY_QUERY", "未指定"),
        revenue_model=_env_or_default("REVENUE_MODEL", "AdSense"),
        goal_action=_env_or_default("GOAL_ACTION", "未指定"),
    )
    logger.info("Running final monetization check")
    review_text = llm_client.generate(review_system, review_prompt, temperature=None)
    review_path = os.getenv("FINAL_CHECK_PATH", os.path.join("out", "final_check.md"))
    _save_text(review_text, review_path)


def _save_text(content: str, output_file: str) -> None:
    output_path = Path(output_file)
    parent_dir = output_path.parent
    if parent_dir and parent_dir != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(content)


def _insert_series_links(article: str) -> str:
    url_a = os.getenv("SERIES_LINK_A")
    url_b = os.getenv("SERIES_LINK_B")
    if not url_a and not url_b:
        return article

    label_a = os.getenv("SERIES_LINK_A_LABEL", "すぐ使う：速報本文テンプレ")
    label_b = os.getenv("SERIES_LINK_B_LABEL", "設定・計測：はてなブログ向け設定")

    block_lines = ["> 次に読む"]
    if url_a:
        block_lines.append(f"> {label_a}：{url_a}")
    if url_b:
        block_lines.append(f"> {label_b}：{url_b}")
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
