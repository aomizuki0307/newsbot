"""WordPress publishing module"""

import base64
import logging
from typing import Any, Dict

import requests

from .utils.retry import wordpress_retry

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """WordPress REST API client for publishing articles"""

    def __init__(self, site_url: str, username: str, app_password: str):
        """Initialize WordPress publisher

        Args:
            site_url: WordPress site URL (e.g., https://example.com)
            username: WordPress username
            app_password: WordPress application password
        """
        self.site_url = site_url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wp/v2/posts"
        self.username = username
        self.app_password = app_password

        # Create basic auth token
        credentials = f"{username}:{app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json"
        }

    @wordpress_retry()
    def publish_draft(self, title: str, content: str) -> Dict[str, Any]:
        """Publish article as draft to WordPress

        Args:
            title: Article title
            content: Article content (HTML or markdown)

        Returns:
            Response dictionary with post ID and URL
        """
        post_data = {
            "title": title,
            "content": content,
            "status": "draft"
        }

        try:
            logger.info(f"Publishing draft to WordPress: {title}")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=post_data,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Draft published successfully: ID={result['id']}, URL={result['link']}")
            return {
                'id': result['id'],
                'url': result['link'],
                'status': result['status']
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to publish to WordPress: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise


def publish_to_wordpress(article: str, wp_url: str, wp_username: str, wp_password: str) -> Dict[str, Any]:
    """Publish article to WordPress as draft

    Args:
        article: Markdown article text
        wp_url: WordPress site URL
        wp_username: WordPress username
        wp_password: WordPress application password

    Returns:
        Dictionary with post ID and URL
    """
    # Extract title from markdown (first heading)
    lines = article.split('\n')
    title = "技術ニュース記事"

    for line in lines:
        if line.startswith('# ') or line.startswith('## '):
            title = line.lstrip('#').strip()
            break

    publisher = WordPressPublisher(wp_url, wp_username, wp_password)
    return publisher.publish_draft(title, article)
