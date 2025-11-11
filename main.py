"""newsbot - AI-powered article aggregation and generation tool

Main entry point for the newsbot application.
"""

import logging
import os
import sys
from typing import List

from dotenv import load_dotenv

from src.collect import ArticleCache, collect_articles
from src.compose import compose_article, save_draft
from src.publish_wordpress import publish_to_wordpress
from src.summarize import summarize_articles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('newsbot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from environment variables

    Returns:
        Dictionary with configuration values
    """
    load_dotenv()

    config = {
        'llm_provider': os.getenv('LLM_PROVIDER', 'openai').lower(),
        'rss_feeds': os.getenv('RSS_FEEDS', '').split(','),
        'cache_duration': int(os.getenv('CACHE_DURATION_HOURS', '24')),
        'wp_url': os.getenv('WORDPRESS_URL'),
        'wp_username': os.getenv('WORDPRESS_USERNAME'),
        'wp_password': os.getenv('WORDPRESS_APP_PASSWORD'),
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


def main():
    """Main execution flow"""
    logger.info("=" * 60)
    logger.info("newsbot starting")
    logger.info("=" * 60)

    try:
        # Load configuration
        config = load_config()

        # Initialize cache
        cache = ArticleCache(
            cache_file='cache.json',
            duration_hours=config['cache_duration']
        )

        # Step 1: Collect articles from RSS feeds
        logger.info("Step 1: Collecting articles from RSS feeds")
        articles = collect_articles(config['rss_feeds'], cache)

        if not articles:
            logger.info("No new articles to process. Exiting.")
            return 0

        # Step 2: Summarize articles
        logger.info("Step 2: Summarizing articles")
        summaries = summarize_articles(articles, provider=config['llm_provider'])

        if not summaries:
            logger.error("No summaries generated. Exiting.")
            return 1

        # Step 3: Compose unified article
        logger.info("Step 3: Composing unified article")
        article = compose_article(summaries, provider=config['llm_provider'])

        # Step 4: Save draft locally
        logger.info("Step 4: Saving draft to draft.md")
        save_draft(article, output_file='draft.md')

        # Step 5: Publish to WordPress (if configured)
        if config['wp_url'] and config['wp_username'] and config['wp_password']:
            logger.info("Step 5: Publishing to WordPress")
            result = publish_to_wordpress(
                article,
                wp_url=config['wp_url'],
                wp_username=config['wp_username'],
                wp_password=config['wp_password']
            )
            logger.info(f"Published to WordPress: {result['url']}")
        else:
            logger.info("Step 5: WordPress not configured, skipping publish")

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
            save_draft(error_msg, output_file='draft.md')
        except Exception as save_error:
            logger.error(f"Failed to save error draft: {save_error}")

        logger.info("=" * 60)
        logger.info("newsbot failed")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
