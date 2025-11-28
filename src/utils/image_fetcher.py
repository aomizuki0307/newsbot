"""Image fetcher utility for article featured images"""

import logging
import os
from typing import Optional
from io import BytesIO

import requests

logger = logging.getLogger(__name__)


class UnsplashImageFetcher:
    """Fetch images from Unsplash API"""

    def __init__(self, access_key: Optional[str] = None):
        """Initialize Unsplash image fetcher

        Args:
            access_key: Unsplash API access key
        """
        self.access_key = access_key or os.getenv("UNSPLASH_ACCESS_KEY")
        self.api_url = "https://api.unsplash.com"

        if not self.access_key:
            logger.warning("UNSPLASH_ACCESS_KEY not set - image fetching disabled")

    def search_image(self, query: str, orientation: str = "landscape") -> Optional[dict]:
        """Search for an image on Unsplash

        Args:
            query: Search query (keywords)
            orientation: Image orientation (landscape, portrait, squarish)

        Returns:
            Dictionary with image data (url, download_location, photographer) or None
        """
        if not self.access_key:
            logger.warning("Cannot search images - API key not configured")
            return None

        try:
            headers = {
                "Authorization": f"Client-ID {self.access_key}"
            }
            params = {
                "query": query,
                "orientation": orientation,
                "per_page": 1
            }

            logger.info(f"Searching Unsplash for: {query}")
            response = requests.get(
                f"{self.api_url}/search/photos",
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data.get("total", 0) == 0:
                logger.warning(f"No images found for query: {query}")
                return None

            result = data["results"][0]
            image_data = {
                "url": result["urls"]["regular"],
                "download_location": result["links"]["download_location"],
                "photographer": result["user"]["name"],
                "photographer_url": result["user"]["links"]["html"],
                "unsplash_url": result["links"]["html"]
            }

            logger.info(f"Found image by {image_data['photographer']}")
            return image_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search Unsplash: {e}")
            return None

    def download_image(self, image_url: str, download_location: Optional[str] = None) -> Optional[BytesIO]:
        """Download image from URL

        Args:
            image_url: Image URL to download
            download_location: Unsplash download tracking URL (optional but recommended)

        Returns:
            BytesIO object containing image data or None
        """
        try:
            # Trigger download tracking (Unsplash API guideline)
            if download_location and self.access_key:
                headers = {"Authorization": f"Client-ID {self.access_key}"}
                requests.get(download_location, headers=headers, timeout=5)

            # Download the actual image
            logger.info(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            return BytesIO(response.content)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return None

    def search_and_download(self, query: str, orientation: str = "landscape") -> Optional[tuple]:
        """Search and download an image in one step

        Args:
            query: Search query
            orientation: Image orientation

        Returns:
            Tuple of (image_data: BytesIO, metadata: dict) or None
        """
        image_data = self.search_image(query, orientation)
        if not image_data:
            return None

        image_file = self.download_image(
            image_data["url"],
            image_data.get("download_location")
        )
        if not image_file:
            return None

        return image_file, image_data


def translate_keywords_for_search(keywords: list) -> str:
    """Translate Japanese keywords to English for better Unsplash results

    Args:
        keywords: List of Japanese keywords

    Returns:
        English search query string
    """
    # Simple keyword mapping (extend as needed)
    translations = {
        "テクノロジー": "technology",
        "健康": "health wellness",
        "暮らし": "lifestyle",
        "エンタメ": "entertainment",
        "経済": "business economy",
        "社会": "society",
        "スポーツ": "sports",
        "教育": "education",
        "AI": "artificial intelligence",
        "人工知能": "artificial intelligence",
        "機械学習": "machine learning",
        "スマートフォン": "smartphone",
        "スマホ": "smartphone"
    }

    english_keywords = []
    for keyword in keywords:
        translated = translations.get(keyword, keyword)
        english_keywords.append(translated)

    # Use first keyword or combine if short
    if len(english_keywords) == 1:
        return english_keywords[0]
    else:
        # Return first keyword for now (Unsplash works better with focused queries)
        return english_keywords[0]
