"""Tests for article collection module"""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest
from unittest.mock import Mock, patch

from src.collect import ArticleCache, collect_rss_urls, extract_article_content


@pytest.fixture
def temp_cache_file():
    """Temporary cache file fixture"""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_article_cache_initialization_creates_empty_cache(temp_cache_file):
    """Test ArticleCache initialization with new cache file"""
    cache = ArticleCache(cache_file=temp_cache_file, duration_hours=24)

    assert cache.cache == {}
    assert cache.duration_hours == 24


def test_article_cache_add_and_is_cached(temp_cache_file):
    """Test adding URLs to cache and checking if cached"""
    cache = ArticleCache(cache_file=temp_cache_file, duration_hours=24)

    url = "https://example.com/article"

    # Initially not cached
    assert not cache.is_cached(url)

    # Add to cache
    cache.add(url)

    # Now should be cached
    assert cache.is_cached(url)


def test_article_cache_expiration(temp_cache_file):
    """Test that cache entries expire after duration"""
    cache = ArticleCache(cache_file=temp_cache_file, duration_hours=1)

    url = "https://example.com/article"

    # Manually add an expired entry
    expired_time = datetime.now() - timedelta(hours=2)
    cache.cache[url] = expired_time.isoformat()

    # Should not be cached (expired)
    assert not cache.is_cached(url)

    # Cache should be cleaned
    assert url not in cache.cache


def test_article_cache_persistence(temp_cache_file):
    """Test that cache persists across instances"""
    url = "https://example.com/article"

    # First instance
    cache1 = ArticleCache(cache_file=temp_cache_file)
    cache1.add(url)

    # Second instance should load the same cache
    cache2 = ArticleCache(cache_file=temp_cache_file)
    assert cache2.is_cached(url)


@patch('src.collect.feedparser.parse')
def test_collect_rss_urls_returns_urls(mock_parse):
    """Test that collect_rss_urls extracts URLs from RSS feeds"""
    mock_feed = Mock()
    mock_feed.bozo = False
    mock_feed.entries = [
        Mock(link='https://example.com/article1'),
        Mock(link='https://example.com/article2'),
    ]
    mock_parse.return_value = mock_feed

    feeds = ['https://example.com/feed.xml']
    urls = collect_rss_urls(feeds)

    assert len(urls) == 2
    assert 'https://example.com/article1' in urls
    assert 'https://example.com/article2' in urls


@patch('src.collect.Article')
def test_extract_article_content_returns_correct_structure(mock_article_class):
    """Test that extract_article_content returns correct dictionary structure"""
    mock_article = Mock()
    mock_article.title = 'Test Article'
    mock_article.text = 'This is the article content.'
    mock_article.publish_date = datetime(2024, 1, 1)
    mock_article_class.return_value = mock_article

    url = 'https://example.com/article'
    result = extract_article_content(url)

    assert result['url'] == url
    assert result['title'] == 'Test Article'
    assert result['text'] == 'This is the article content.'
    assert result['publish_date'] == '2024-01-01 00:00:00'


@patch('src.collect.Article')
def test_extract_article_content_calls_download_and_parse(mock_article_class):
    """Test that extract_article_content calls download() and parse()"""
    mock_article = Mock()
    mock_article.title = 'Test'
    mock_article.text = 'Content'
    mock_article.publish_date = None
    mock_article_class.return_value = mock_article

    extract_article_content('https://example.com/article')

    mock_article.download.assert_called_once()
    mock_article.parse.assert_called_once()
