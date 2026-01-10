"""newsbot - AI-powered article aggregation and generation tool

Main entry point for the newsbot application.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values

from src.collect import ArticleCache, collect_articles
from src.compose import compose_article, save_draft
from src.publish_hatena import publish_to_hatena_with_image
from src.publish_wordpress import publish_to_wordpress
from src.summarize import summarize_articles


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging():
    """Configure logging with optional JSON output."""
    json_logs = os.getenv("JSON_LOGS", "false").lower() == "true"
    formatter: logging.Formatter
    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handlers = [
        logging.StreamHandler(),
        logging.FileHandler('newsbot.log', encoding='utf-8')
    ]

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(logging.INFO)

    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


logger = logging.getLogger(__name__)


def _apply_dotenv_values(
    values: dict,
    *,
    override_keys: Optional[set[str]] = None,
    override_all: bool = False,
) -> None:
    if not values:
        return
    override_keys = override_keys or set()
    for key, value in values.items():
        if value is None:
            continue
        if override_all or key in override_keys or key not in os.environ:
            os.environ[key] = value


def _load_dotenv_files(profile: Optional[str]) -> dict:
    base_path = Path(".env")
    base_values = dotenv_values(base_path) if base_path.exists() else {}
    _apply_dotenv_values(base_values)

    profile_loaded = False
    profile_path = None
    if profile:
        os.environ.setdefault("NEWSBOT_PROFILE", profile)
        os.environ.setdefault("PROMPT_VARIANT", profile)
        profile_path = Path(f".env.{profile}")
        if profile_path.exists():
            override_all = os.getenv("NEWSBOT_DOTENV_OVERRIDE", "false").lower() == "true"
            override_keys = set(base_values.keys())
            profile_values = dotenv_values(profile_path)
            _apply_dotenv_values(
                profile_values,
                override_keys=override_keys,
                override_all=override_all,
            )
            profile_loaded = True

    return {
        "base_loaded": bool(base_values),
        "profile_loaded": profile_loaded,
        "profile_path": str(profile_path) if profile_path else None,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="newsbot runner")
    parser.add_argument(
        "--profile",
        help="Optional profile name (loads .env.<profile> and sets PROMPT_VARIANT)",
    )
    return parser.parse_args()


def _parse_positive_int(env_name: str) -> Optional[int]:
    """Return positive int or None for empty/zero env values."""
    value = os.getenv(env_name)
    if value is None:
        return None
    value = value.strip()
    if not value or value == "0":
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be a positive integer") from exc
    return parsed if parsed > 0 else None


def load_config():
    """Load configuration from environment variables

    Returns:
        Dictionary with configuration values
    """
    config = {
        'llm_provider': os.getenv('LLM_PROVIDER', 'openai').lower(),
        'rss_feeds': os.getenv('RSS_FEEDS', '').split(','),
        'cache_duration': int(os.getenv('CACHE_DURATION_HOURS', '24')),
        'wp_url': os.getenv('WORDPRESS_URL'),
        'wp_username': os.getenv('WORDPRESS_USERNAME'),
        'wp_password': os.getenv('WORDPRESS_APP_PASSWORD'),
        'publish_platform': os.getenv('PUBLISH_PLATFORM', 'wordpress').lower(),
        'hatena_id': os.getenv('HATENA_ID'),
        'hatena_blog_id': os.getenv('HATENA_BLOG_ID'),
        'hatena_api_key': os.getenv('HATENA_API_KEY'),
        'hatena_atom_endpoint': os.getenv('HATENA_ATOM_ENDPOINT'),
        'hatena_categories': os.getenv('HATENA_CATEGORIES'),
        'hatena_draft': os.getenv('HATENA_DRAFT'),
        'hatena_content_type': os.getenv('HATENA_CONTENT_TYPE'),
        'max_articles_per_run': _parse_positive_int('MAX_ARTICLES_PER_RUN'),
        'max_tokens_per_run': _parse_positive_int('MAX_TOKENS_PER_RUN'),
        'allowlist_path': os.getenv('ALLOWLIST_PATH', 'config/allowlist.txt'),
        'draft_path': os.getenv('DRAFT_PATH', os.path.join('out', 'draft.md')),
    }

    # Validate required fields
    if not config['rss_feeds'] or config['rss_feeds'] == ['']:
        logger.error("RSS_FEEDS not configured in .env")
        raise ValueError("RSS_FEEDS is required")

    # Filter empty feeds
    config['rss_feeds'] = [f.strip() for f in config['rss_feeds'] if f.strip()]

    # Validate LLM provider
    if config['llm_provider'] not in ['openai', 'anthropic']:
        logger.error(f"Invalid LLM_PROVIDER: {config['llm_provider']}")
        raise ValueError("LLM_PROVIDER must be 'openai' or 'anthropic'")

    # Check API keys
    if config['llm_provider'] == 'openai' and not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not set")
        raise ValueError("OPENAI_API_KEY is required when using OpenAI")

    if config['llm_provider'] == 'anthropic' and not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("ANTHROPIC_API_KEY not set")
        raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic")

    logger.info(f"Configuration loaded: LLM={config['llm_provider']}, "
                f"RSS feeds={len(config['rss_feeds'])}, "
                f"Cache={config['cache_duration']}h")

    return config


def _emit_metrics(metrics: dict, start_time: float):
    """Log final metrics in a single structured line."""
    metrics["duration_seconds"] = round(time.perf_counter() - start_time, 2)
    logger.info("run_metrics=%s", json.dumps(metrics, ensure_ascii=False))


def main():
    """Main execution flow"""
    args = _parse_args()
    env_info = _load_dotenv_files(args.profile)
    configure_logging()

    if args.profile:
        logger.info("Profile selected: %s", args.profile)
    if env_info["profile_path"] and not env_info["profile_loaded"]:
        logger.info("Profile dotenv not found: %s", env_info["profile_path"])

    logger.info("=" * 60)
    logger.info("newsbot starting")
    logger.info("=" * 60)

    start_time = time.perf_counter()
    metrics = {
        "articles_collected": 0,
        "articles_after_limit": 0,
        "summaries_generated": 0,
        "summaries_failed": 0,
        "tokens_estimated": 0,
        "token_limit_reached": False,
        "wordpress_published": False,
        "hatena_published": False,
        "publish_platform": None,
    }
    draft_path = os.getenv('DRAFT_PATH', os.path.join('out', 'draft.md'))

    try:
        # Load configuration
        config = load_config()
        draft_path = config['draft_path']

        # Initialize cache
        cache = ArticleCache(
            cache_file='cache.json',
            duration_hours=config['cache_duration']
        )

        # Step 1: Collect articles from RSS feeds
        logger.info("Step 1: Collecting articles from RSS feeds")
        articles = collect_articles(
            config['rss_feeds'],
            cache,
            allowlist_path=config['allowlist_path'],
        )
        metrics["articles_collected"] = len(articles)

        if not articles:
            logger.info("No new articles to process. Exiting.")
            _emit_metrics(metrics, start_time)
            return 0

        # Enforce article ceiling before expensive LLM calls
        max_articles = config.get('max_articles_per_run')
        if max_articles and len(articles) > max_articles:
            logger.warning(
                "MAX_ARTICLES_PER_RUN=%s enforced. Truncating from %s to %s articles.",
                max_articles,
                len(articles),
                max_articles,
            )
            articles = articles[:max_articles]
        metrics["articles_after_limit"] = len(articles)

        # Step 2: Summarize articles
        logger.info("Step 2: Summarizing articles")
        summary_result = summarize_articles(
            articles,
            provider=config['llm_provider'],
            max_tokens=config.get('max_tokens_per_run'),
        )
        summaries = summary_result.summaries
        metrics["summaries_generated"] = len(summaries)
        metrics["summaries_failed"] = summary_result.failed
        metrics["tokens_estimated"] = summary_result.estimated_tokens
        metrics["token_limit_reached"] = summary_result.limit_reached

        if not summaries:
            logger.error("No summaries generated. Exiting.")
            _emit_metrics(metrics, start_time)
            return 1

        if summary_result.failed:
            logger.warning("Summarization had %s failures.", summary_result.failed)

        if summary_result.limit_reached:
            logger.warning("Token budget reached during summarization; partial output will be used.")

        # Step 3: Compose unified article
        logger.info("Step 3: Composing unified article")
        article = compose_article(summaries, provider=config['llm_provider'])

        # Step 4: Save draft locally
        logger.info("Step 4: Saving draft to %s", draft_path)
        save_draft(article, output_file=draft_path)

        # Step 5: Publish to platform
        publish_platform = config.get("publish_platform", "wordpress")
        metrics["publish_platform"] = publish_platform

        if publish_platform == "hatena":
            if config["hatena_id"] and (config["hatena_api_key"] or config["hatena_atom_endpoint"]):
                logger.info("Step 5: Publishing to Hatena Blog with featured image")
                result = publish_to_hatena_with_image(
                    article,
                    hatena_id=config["hatena_id"],
                    blog_id=config["hatena_blog_id"],
                    api_key=config["hatena_api_key"],
                    endpoint=config["hatena_atom_endpoint"],
                    categories=config["hatena_categories"].split(",") if config["hatena_categories"] else None,
                    draft=None
                    if config["hatena_draft"] is None
                    else str(config["hatena_draft"]).strip().lower() in {"1", "true", "yes", "on"},
                    content_type=config["hatena_content_type"],
                )
                if result.get("url"):
                    logger.info("Published to Hatena Blog: %s", result["url"])
                else:
                    logger.info("Published to Hatena Blog (URL not returned)")
                metrics["hatena_published"] = True
            else:
                logger.info("Step 5: Hatena not configured, skipping publish")
        elif publish_platform == "wordpress":
            if config['wp_url'] and config['wp_username'] and config['wp_password']:
                logger.info("Step 5: Publishing to WordPress")
                result = publish_to_wordpress(
                    article,
                    wp_url=config['wp_url'],
                    wp_username=config['wp_username'],
                    wp_password=config['wp_password']
                )
                logger.info(f"Published to WordPress: {result['url']}")
                metrics["wordpress_published"] = True
            else:
                logger.info("Step 5: WordPress not configured, skipping publish")
        else:
            logger.warning("Step 5: Unknown PUBLISH_PLATFORM=%s, skipping publish", publish_platform)

        _emit_metrics(metrics, start_time)
        logger.info("=" * 60)
        logger.info("newsbot completed successfully")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

        # Try to save whatever we have as draft
        try:
            logger.info("Attempting to save partial draft")
            error_msg = f"# エラーが発生しました\n\n```\n{str(e)}\n```\n\n処理を中断しました。"
            save_draft(error_msg, output_file=draft_path)
        except Exception as save_error:
            logger.error(f"Failed to save error draft: {save_error}")

        _emit_metrics(metrics, start_time)
        logger.info("=" * 60)
        logger.info("newsbot failed")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
