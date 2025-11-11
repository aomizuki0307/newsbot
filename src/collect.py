"""RSS feed collection and article extraction module"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Set
from urllib.parse import urlparse

import feedparser
import requests
from newspaper import Article

logger = logging.getLogger(__name__)


class ArticleCache:
    """Simple JSON-based cache for processed articles"""

    def __init__(self, cache_file: str = "cache.json", duration_hours: int = 24):
        self.cache_file = cache_file
        self.duration_hours = duration_hours
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    def is_cached(self, url: str) -> bool:
        """Check if URL was processed recently"""
        if url not in self.cache:
            return False

        cached_time = datetime.fromisoformat(self.cache[url])
        expiry = cached_time + timedelta(hours=self.duration_hours)

        if datetime.now() > expiry:
            del self.cache[url]
            return False

        return True

    def add(self, url: str):
        """Add URL to cache"""
        self.cache[url] = datetime.now().isoformat()
        self._save_cache()


def collect_rss_urls(rss_feeds: List[str]) -> List[str]:
    """Collect article URLs from RSS feeds

    Args:
        rss_feeds: List of RSS feed URLs

    Returns:
        List of article URLs
    """
    urls = []

    for feed_url in rss_feeds:
        try:
            logger.info(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parse warning for {feed_url}: {feed.bozo_exception}")

            for entry in feed.entries:
                if hasattr(entry, 'link'):
                    urls.append(entry.link)

            logger.info(f"Found {len(feed.entries)} entries in {feed_url}")

        except Exception as e:
            logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")

    return urls


def extract_article_content(url: str) -> Dict[str, str]:
    """Extract article content from URL using newspaper3k

    Args:
        url: Article URL

    Returns:
        Dictionary with 'url', 'title', 'text', 'publish_date'
    """
    try:
        article = Article(url)
        article.download()
        article.parse()

        return {
            'url': url,
            'title': article.title,
            'text': article.text,
            'publish_date': str(article.publish_date) if article.publish_date else None,
        }

    except Exception as e:
        logger.error(f"Failed to extract article from {url}: {e}")
        raise


def collect_articles(rss_feeds: List[str], cache: ArticleCache) -> List[Dict[str, str]]:
    """Collect and extract articles from RSS feeds with caching

    Args:
        rss_feeds: List of RSS feed URLs
        cache: ArticleCache instance for deduplication

    Returns:
        List of article dictionaries
    """
    urls = collect_rss_urls(rss_feeds)
    logger.info(f"Collected {len(urls)} URLs from RSS feeds")

    # Deduplicate URLs
    unique_urls = list(dict.fromkeys(urls))
    logger.info(f"Unique URLs: {len(unique_urls)}")

    # Filter cached URLs
    new_urls = [url for url in unique_urls if not cache.is_cached(url)]
    logger.info(f"New URLs (not cached): {len(new_urls)}")

    if not new_urls:
        logger.info("No new articles to process")
        return []

    articles = []
    for url in new_urls:
        try:
            article = extract_article_content(url)

            # Basic validation
            if article['text'] and len(article['text']) > 100:
                articles.append(article)
                cache.add(url)
                logger.info(f"Extracted article: {article['title'][:50]}")
            else:
                logger.warning(f"Article too short or empty: {url}")

        except Exception as e:
            logger.error(f"Skipping article {url}: {e}")

    logger.info(f"Successfully extracted {len(articles)} articles")
    return articles
