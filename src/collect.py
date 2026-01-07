"""RSS feed collection and article extraction module"""

import ipaddress
import json
import logging
import os
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

import feedparser
from newspaper import Article

logger = logging.getLogger(__name__)


PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


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


def load_allowlist(path: str) -> Set[str]:
    """Load allowed domains from text file."""
    allowlist_path = Path(path)
    if not allowlist_path.exists():
        raise FileNotFoundError(f"Allowlist not found: {path}")

    domains: Set[str] = set()
    with allowlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            domains.add(stripped.lower())

    if not domains:
        raise ValueError(f"Allowlist at {path} is empty.")
    return domains


def _normalize_domain(host: str) -> str:
    return host.lower().strip(".") if host else ""


def _domain_in_allowlist(domain: str, allowlist: Set[str]) -> bool:
    return any(
        domain == allowed or domain.endswith(f".{allowed}")
        for allowed in allowlist
    )


def _is_public_ip(ip_str: str) -> bool:
    ip_obj = ipaddress.ip_address(ip_str)
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast:
        return False
    for network in PRIVATE_NETWORKS:
        if ip_obj in network:
            return False
    return True


def _host_addresses(hostname: str) -> List[str]:
    try:
        return list({info[4][0] for info in socket.getaddrinfo(hostname, None)})
    except socket.gaierror as exc:
        logger.warning("Failed to resolve %s: %s", hostname, exc)
        return []


def validate_article_url(url: str, allowlist: Set[str]) -> Tuple[bool, str]:
    """Validate URL against HTTPS, allowlist, and SSRF safeguards."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return False, "non-https"

    domain = _normalize_domain(parsed.hostname or "")
    if not domain:
        return False, "missing-host"

    if not _domain_in_allowlist(domain, allowlist):
        return False, "domain-not-allowlisted"

    addresses = _host_addresses(domain)
    if not addresses:
        return False, "unresolved-host"

    for ip_str in addresses:
        if not _is_public_ip(ip_str):
            return False, f"forbidden-ip:{ip_str}"

    return True, ""


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
        Dictionary with 'url', 'title', 'text', 'summary', 'publish_date'
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        # Some sites (e.g., NHK) return very short bodies via newspaper3k.
        # Keep meta_description/summary as fallback so we don't drop the article.
        summary = article.summary if hasattr(article, "summary") else None
        if not summary and hasattr(article, "meta_description"):
            summary = getattr(article, "meta_description")

        return {
            'url': url,
            'title': article.title,
            'text': article.text,
            'summary': summary,
            'publish_date': str(article.publish_date) if article.publish_date else None,
        }

    except Exception as e:
        logger.error(f"Failed to extract article from {url}: {e}")
        raise


def collect_articles(
    rss_feeds: List[str],
    cache: ArticleCache,
    allowlist_path: str = "config/allowlist.txt",
) -> List[Dict[str, str]]:
    """Collect and extract articles from RSS feeds with caching and security checks

    Args:
        rss_feeds: List of RSS feed URLs
        cache: ArticleCache instance for deduplication
        allowlist_path: Path to file containing allowed domains

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

    try:
        allowed_domains = load_allowlist(allowlist_path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Allowlist error: %s", exc)
        raise

    secure_urls = []
    for candidate_url in new_urls:
        allowed, reason = validate_article_url(candidate_url, allowed_domains)
        if not allowed:
            logger.info("Skipping URL due to %s: %s", reason, candidate_url)
            continue
        secure_urls.append(candidate_url)

    if not secure_urls:
        logger.info("No URLs passed security filters.")
        return []

    articles = []
    for url in secure_urls:
        try:
            article = extract_article_content(url)

            # Choose best-available body text
            body = article.get('text') or article.get('summary')

            # Basic validation
            if body and len(body) > 50:
                # Store chosen body back into text field so downstream uses it
                article['text'] = body
                articles.append(article)
                cache.add(url)
                logger.info(f"Extracted article: {article['title'][:50]}")
            else:
                logger.warning(f"Article too short or empty: {url}")

        except Exception as e:
            logger.error(f"Skipping article {url}: {e}")

    logger.info(f"Successfully extracted {len(articles)} articles")
    return articles
