"""Article categorization utility based on keywords"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ArticleCategorizer:
    """Categorize articles based on keyword matching"""

    def __init__(self, config_path: str = "config/category_keywords.json"):
        """Initialize categorizer with keyword mappings

        Args:
            config_path: Path to keyword mapping configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.default_category_id = self.config.get("default_category_id")
        self.category_keywords = self.config.get("category_keywords", {})
        self.tag_keywords = self.config.get("tag_keywords", {})

    def _load_config(self) -> Dict:
        """Load keyword mapping configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config file: {e}")
            return {}

    def categorize(self, title: str, content: str) -> Tuple[List[int], List[str]]:
        """Categorize article based on title and content

        Args:
            title: Article title
            content: Article content

        Returns:
            Tuple of (category_ids, tag_names)
        """
        text = f"{title} {content}".lower()

        # Determine categories
        categories = self._match_categories(text)
        if not categories and self.default_category_id:
            categories = [self.default_category_id]

        # Determine tags
        tags = self._match_tags(text)

        logger.info(f"Categorized article: categories={categories}, tags={tags}")
        return categories, tags

    def _match_categories(self, text: str) -> List[int]:
        """Match categories based on keywords

        Args:
            text: Text to search for keywords (lowercase)

        Returns:
            List of category IDs
        """
        matched_categories = []

        for category_id, keywords in self.category_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                try:
                    matched_categories.append(int(category_id))
                except ValueError:
                    logger.warning(f"Invalid category ID: {category_id}")

        return matched_categories

    def _match_tags(self, text: str) -> List[str]:
        """Match tags based on keywords

        Args:
            text: Text to search for keywords (lowercase)

        Returns:
            List of tag names
        """
        matched_tags = []

        for tag_name, keywords in self.tag_keywords.items():
            if any(keyword.lower() in text for keyword in keywords):
                matched_tags.append(tag_name)

        return matched_tags
