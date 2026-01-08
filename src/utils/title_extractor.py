"""Title extraction utility for articles"""

import logging
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class TitleExtractor(HTMLParser):
    """Extract title from HTML content"""

    def __init__(self):
        super().__init__()
        self.title = None
        self.current_tag = None
        self.capture_data = False

    def handle_starttag(self, tag, attrs):
        if self.title is None and tag in ['h1', 'h2']:
            self.current_tag = tag
            self.capture_data = True

    def handle_data(self, data):
        if self.capture_data:
            self.title = data.strip()
            self.capture_data = False

    def handle_endtag(self, tag):
        if tag == self.current_tag:
            self.capture_data = False


def extract_title_from_html(content: str, default: str = "newsbot") -> str:
    """Extract title from HTML content

    Args:
        content: HTML content
        default: Default title if extraction fails

    Returns:
        Extracted title or default
    """
    try:
        parser = TitleExtractor()
        parser.feed(content)

        if parser.title:
            # Truncate if too long (Hatena has limits)
            title = parser.title[:100]
            logger.info(f"Extracted title: {title}")
            return title
        else:
            logger.warning("No title found in HTML, using default")
            return default
    except Exception as e:
        logger.error(f"Failed to extract title: {e}")
        return default


def extract_title_from_markdown(content: str, default: str = "newsbot") -> str:
    """Extract title from Markdown content (fallback for markdown format)

    Args:
        content: Markdown content
        default: Default title if extraction fails

    Returns:
        Extracted title or default
    """
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if line.startswith('# ') or line.startswith('## '):
            title = line.lstrip('#').strip()[:100]
            logger.info(f"Extracted markdown title: {title}")
            return title

    logger.warning("No markdown title found, using default")
    return default


def extract_title(content: str, default: str = "newsbot") -> str:
    """Smart title extraction supporting both HTML and Markdown

    Args:
        content: Article content (HTML or Markdown)
        default: Default title if extraction fails

    Returns:
        Extracted title or default
    """
    # Detect format by looking for HTML tags
    if '<h1' in content or '<h2' in content or '<p>' in content:
        return extract_title_from_html(content, default)
    else:
        return extract_title_from_markdown(content, default)
