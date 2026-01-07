"""WordPress publishing module"""

import base64
import logging
from typing import Any, Dict, List, Optional
from io import BytesIO

import requests

from .utils.retry import wordpress_retry
from .utils.categorizer import ArticleCategorizer
from .utils.image_fetcher import UnsplashImageFetcher, translate_keywords_for_search

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
        self.tags_api_url = f"{self.site_url}/wp-json/wp/v2/tags"
        self.media_api_url = f"{self.site_url}/wp-json/wp/v2/media"
        self.username = username
        self.app_password = app_password

        # Create basic auth token
        credentials = f"{username}:{app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json"
        }

        # Cache for tag name to ID mapping
        self._tag_cache: Dict[str, int] = {}

    def _get_or_create_tag(self, tag_name: str) -> int:
        """Get tag ID by name, create if not exists

        Args:
            tag_name: Tag name

        Returns:
            Tag ID
        """
        # Check cache first
        if tag_name in self._tag_cache:
            return self._tag_cache[tag_name]

        try:
            # Search for existing tag
            response = requests.get(
                self.tags_api_url,
                headers=self.headers,
                params={"search": tag_name},
                timeout=10
            )
            response.raise_for_status()
            tags = response.json()

            # Check if exact match exists
            for tag in tags:
                if tag["name"].lower() == tag_name.lower():
                    tag_id = tag["id"]
                    self._tag_cache[tag_name] = tag_id
                    logger.info(f"Found existing tag: {tag_name} (ID: {tag_id})")
                    return tag_id

            # Tag doesn't exist, create it
            response = requests.post(
                self.tags_api_url,
                headers=self.headers,
                json={"name": tag_name},
                timeout=10
            )
            response.raise_for_status()
            tag_data = response.json()
            tag_id = tag_data["id"]
            self._tag_cache[tag_name] = tag_id
            logger.info(f"Created new tag: {tag_name} (ID: {tag_id})")
            return tag_id

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get/create tag '{tag_name}': {e}")
            return None

    def _get_tag_ids(self, tag_names: List[str]) -> List[int]:
        """Convert tag names to tag IDs

        Args:
            tag_names: List of tag names

        Returns:
            List of tag IDs
        """
        tag_ids = []
        for tag_name in tag_names:
            tag_id = self._get_or_create_tag(tag_name)
            if tag_id is not None:
                tag_ids.append(tag_id)
        return tag_ids

    def upload_media(self, image_data: BytesIO, filename: str, alt_text: str = "") -> Optional[tuple]:
        """Upload media to WordPress

        Args:
            image_data: Image data as BytesIO
            filename: Filename for the media
            alt_text: Alternative text for the image

        Returns:
            Tuple of (media_id, source_url) or None on failure
        """
        try:
            # Prepare headers for media upload
            credentials = f"{self.username}:{self.app_password}"
            token = base64.b64encode(credentials.encode()).decode()

            # Determine MIME type from filename
            mime_type = "image/jpeg"
            if filename.lower().endswith(".png"):
                mime_type = "image/png"
            elif filename.lower().endswith(".gif"):
                mime_type = "image/gif"
            elif filename.lower().endswith(".webp"):
                mime_type = "image/webp"

            headers = {
                "Authorization": f"Basic {token}",
                "Content-Type": mime_type,
                "Content-Disposition": f'attachment; filename="{filename}"'
            }

            # Upload media
            logger.info(f"Uploading media: {filename}")
            response = requests.post(
                self.media_api_url,
                headers=headers,
                data=image_data.getvalue(),
                timeout=30
            )
            response.raise_for_status()
            media = response.json()

            media_id = media["id"]
            source_url = media["source_url"]
            logger.info(f"Media uploaded successfully: ID={media_id}, URL={source_url}")

            # Set alt text if provided
            if alt_text:
                alt_headers = {
                    "Authorization": f"Basic {token}",
                    "Content-Type": "application/json"
                }
                requests.post(
                    f"{self.media_api_url}/{media_id}",
                    headers=alt_headers,
                    json={"alt_text": alt_text},
                    timeout=10
                )

            return (media_id, source_url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload media: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    @wordpress_retry()
    def publish_draft(self, title: str, content: str, categories: List[int] = None, tags: List[str] = None, featured_media: Optional[int] = None) -> Dict[str, Any]:
        """Publish article as draft to WordPress

        Args:
            title: Article title
            content: Article content (HTML or markdown)
            categories: List of category IDs (optional)
            tags: List of tag names (optional)
            featured_media: Media ID for featured image (optional)

        Returns:
            Response dictionary with post ID and URL
        """
        post_data = {
            "title": title,
            "content": content,
            "status": "draft"
        }

        # Add categories if provided
        if categories:
            post_data["categories"] = categories

        # Add tags if provided (convert names to IDs)
        if tags:
            tag_ids = self._get_tag_ids(tags)
            if tag_ids:
                post_data["tags"] = tag_ids

        # Add featured image if provided
        if featured_media:
            post_data["featured_media"] = featured_media

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
    """Publish article to WordPress as draft with automatic categorization and featured image

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

    # Categorize article based on title and content
    categorizer = ArticleCategorizer()
    categories, tags = categorizer.categorize(title, article)

    logger.info(f"Auto-categorized: title='{title}', categories={categories}, tags={tags}")

    publisher = WordPressPublisher(wp_url, wp_username, wp_password)

    # Fetch and upload featured image
    featured_media_id = None
    image_url = None
    image_fetcher = UnsplashImageFetcher()

    if tags:
        # Use first tag as search query (translated to English)
        search_query = translate_keywords_for_search(tags)
        logger.info(f"Searching for featured image with query: {search_query}")

        result = image_fetcher.search_and_download(search_query)
        if result:
            image_file, image_metadata = result

            # Upload to WordPress
            filename = f"{search_query.replace(' ', '_')}.jpg"
            alt_text = f"{title} - Photo by {image_metadata['photographer']} on Unsplash"

            upload_result = publisher.upload_media(image_file, filename, alt_text)

            if upload_result:
                featured_media_id, image_url = upload_result
                logger.info(f"Featured image set: {image_metadata['photographer']} ({image_metadata['unsplash_url']})")

                # Insert image into article content (after title)
                image_credit = f"Photo by {image_metadata['photographer']} on Unsplash"
                image_block = f'\n\n<!-- wp:image {{"id":{featured_media_id},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{image_url}" alt="{alt_text}" class="wp-image-{featured_media_id}"/><figcaption class="wp-element-caption">{image_credit}</figcaption></figure>\n<!-- /wp:image -->\n\n'

                # Find first line break after title and insert image
                lines = article.split('\n', 2)
                if len(lines) >= 2:
                    article = lines[0] + image_block + '\n'.join(lines[1:])
                else:
                    article = lines[0] + image_block

                logger.info("Image embedded in article content")
        else:
            logger.warning("Failed to fetch featured image from Unsplash")

    return publisher.publish_draft(
        title,
        article,
        categories=categories,
        tags=tags,
        featured_media=featured_media_id
    )
