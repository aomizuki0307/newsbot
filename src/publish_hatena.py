"""Publish articles to Hatena Blog via AtomPub."""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Iterable, Optional

import requests

from src.utils.categorizer import ArticleCategorizer
from src.utils.image_fetcher import UnsplashImageFetcher, translate_keywords_for_search
from src.utils.hatena_fotolife import HatenaFotolifeUploader
from src.utils.title_extractor import extract_title
from src.utils.text_formatting import format_markdown_paragraphs

logger = logging.getLogger(__name__)

NS_ATOM = "http://www.w3.org/2005/Atom"
NS_APP = "http://www.w3.org/2007/app"

ET.register_namespace("", NS_ATOM)
ET.register_namespace("app", NS_APP)

_GENERIC_TITLES = {"導入", "本論", "まとめ", "はじめに", "結論"}


def _default_title() -> str:
    now_jst = datetime.utcnow() + timedelta(hours=9)
    return f"ニュースまとめ（{now_jst:%Y-%m-%d}）"


def _bool_from_env(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_categories(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _build_atom_entry(
    title: str,
    content: str,
    *,
    author: str,
    categories: Iterable[str],
    draft: bool,
    content_type: str,
) -> bytes:
    entry = ET.Element(ET.QName(NS_ATOM, "entry"))

    title_el = ET.SubElement(entry, ET.QName(NS_ATOM, "title"))
    title_el.text = title

    author_el = ET.SubElement(entry, ET.QName(NS_ATOM, "author"))
    name_el = ET.SubElement(author_el, ET.QName(NS_ATOM, "name"))
    name_el.text = author

    content_el = ET.SubElement(entry, ET.QName(NS_ATOM, "content"))
    content_el.set("type", content_type)
    content_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    content_el.text = content

    for category in categories:
        cat_el = ET.SubElement(entry, ET.QName(NS_ATOM, "category"))
        cat_el.set("term", category)

    if draft:
        control_el = ET.SubElement(entry, ET.QName(NS_APP, "control"))
        draft_el = ET.SubElement(control_el, ET.QName(NS_APP, "draft"))
        draft_el.text = "yes"

    return ET.tostring(entry, encoding="utf-8", xml_declaration=True)


def _extract_entry_url(response_text: str) -> Optional[str]:
    try:
        root = ET.fromstring(response_text)
    except ET.ParseError:
        logger.warning("Failed to parse Hatena response XML.")
        return None

    for link in root.findall(f"{{{NS_ATOM}}}link"):
        if link.attrib.get("rel") == "alternate":
            return link.attrib.get("href")
    return None


def _ensure_h1_title(article: str, title: str) -> str:
    lines = article.splitlines()
    first_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_idx = idx
            break
    if first_idx is None:
        return f"# {title}\n"

    first_line = lines[first_idx].lstrip()
    if first_line.startswith("# "):
        current = first_line[2:].strip()
        if current in _GENERIC_TITLES:
            lines[first_idx] = f"# {title}"
            return "\n".join(lines)
        return article

    lines.insert(first_idx, f"# {title}")
    lines.insert(first_idx + 1, "")
    return "\n".join(lines)


def publish_to_hatena(
    article: str,
    *,
    title: Optional[str] = None,
    hatena_id: Optional[str] = None,
    blog_id: Optional[str] = None,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    categories: Optional[Iterable[str]] = None,
    draft: Optional[bool] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """Publish an article to Hatena Blog.

    Returns a dict with the published URL (if available) and response text.
    """
    hatena_id = hatena_id or os.getenv("HATENA_ID")
    blog_id = blog_id or os.getenv("HATENA_BLOG_ID")
    api_key = api_key or os.getenv("HATENA_API_KEY")
    endpoint = endpoint or os.getenv("HATENA_ATOM_ENDPOINT")
    if content_type is None:
        content_type = os.getenv("HATENA_CONTENT_TYPE")
    content_type = (content_type or "").strip()
    if not content_type:
        content_type = "text/x-markdown"

    if not endpoint:
        if not hatena_id or not blog_id:
            raise ValueError("HATENA_ATOM_ENDPOINT or (HATENA_ID, HATENA_BLOG_ID) is required")
        endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom/entry"

    if not hatena_id or not api_key:
        raise ValueError("HATENA_ID and HATENA_API_KEY are required for Hatena publishing")

    if categories is None:
        categories = _split_categories(os.getenv("HATENA_CATEGORIES"))

    if draft is None:
        draft = _bool_from_env(os.getenv("HATENA_DRAFT"))

    if article:
        article = article.replace("\r\n", "\n").replace("\r", "\n")

    format_paragraphs = _bool_from_env(os.getenv("HATENA_FORMAT_PARAGRAPHS", "true"))
    if format_paragraphs:
        try:
            sentences = int(os.getenv("HATENA_PARAGRAPH_SENTENCES", "2") or "2")
        except ValueError:
            sentences = 2
        if content_type.lower().startswith("text/x-markdown") or content_type.lower().startswith("text/markdown"):
            article = format_markdown_paragraphs(article, sentences_per_paragraph=sentences)
            logger.info("Applied markdown paragraph formatting: %s sentences/paragraph", sentences)

    # Extract title from article content if not provided
    if title is None:
        title = extract_title(article, default="newsbot")
    if title and title.strip() in _GENERIC_TITLES:
        logger.warning("Extracted generic title '%s'; using fallback.", title)
        title = None

    publish_title = title or os.getenv("HATENA_TITLE") or _default_title()

    article = _ensure_h1_title(article, publish_title)

    payload = _build_atom_entry(
        publish_title,
        article,
        author=hatena_id,
        categories=categories,
        draft=draft,
        content_type=content_type,
    )

    headers = {"Content-Type": "application/atom+xml;type=entry;charset=utf-8"}
    logger.info("Publishing to Hatena Blog: %s", publish_title)
    response = requests.post(
        endpoint,
        data=payload,
        headers=headers,
        auth=(hatena_id, api_key),
        timeout=timeout,
    )
    response.raise_for_status()

    url = _extract_entry_url(response.text)
    return {"url": url, "response": response.text}


def publish_to_hatena_with_image(
    article: str,
    *,
    title: Optional[str] = None,
    hatena_id: Optional[str] = None,
    blog_id: Optional[str] = None,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    categories: Optional[Iterable[str]] = None,
    draft: Optional[bool] = None,
    content_type: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """Publish article to Hatena Blog with automatic title extraction and featured image

    This is the enhanced version that:
    1. Extracts title from article content if not provided
    2. Categorizes article to get tags
    3. Fetches image from Unsplash based on tags
    4. Uploads image to Hatena Fotolife
    5. Embeds image in article
    6. Publishes to Hatena Blog

    Args:
        article: Article content (HTML or Markdown)
        (other parameters same as publish_to_hatena)

    Returns:
        Dictionary with published URL and response
    """
    # Extract title if not provided
    if title is None:
        title = extract_title(article, default="newsbot")
    if title and title.strip() in _GENERIC_TITLES:
        logger.warning("Extracted generic title '%s'; using fallback.", title)
        title = _default_title()

    logger.info(f"Publishing to Hatena with title: {title}")

    # Categorize article to get tags for image search
    categorizer = ArticleCategorizer()
    _, tags = categorizer.categorize(title, article)

    article_with_image = article

    # Fetch and upload featured image
    if tags:
        search_query = translate_keywords_for_search(tags)
        logger.info(f"Searching for featured image with query: {search_query}")

        image_fetcher = UnsplashImageFetcher()
        result = image_fetcher.search_and_download(search_query)

        if result:
            image_file, image_metadata = result

            # Upload to Hatena Fotolife
            fotolife = HatenaFotolifeUploader()
            filename = f"{search_query.replace(' ', '_')}.jpg"

            image_syntax = fotolife.upload_image(
                image_file,
                filename,
                title=f"{title} - Featured Image"
            )

            if image_syntax:
                logger.info(f"Featured image uploaded: {image_metadata['photographer']}")

                # Embed image in article (Hatena syntax)
                # Insert after first heading or at the beginning
                image_credit = f"\n\n{image_syntax}\n\n*Photo by {image_metadata['photographer']} on Unsplash*\n\n"

                # Find insertion point (after first <h2> or at start)
                if '<h2>' in article:
                    # Insert after first </h2>
                    parts = article.split('</h2>', 1)
                    article_with_image = parts[0] + '</h2>' + image_credit + (parts[1] if len(parts) > 1 else '')
                else:
                    # Insert at beginning
                    article_with_image = image_credit + article

                logger.info("Image embedded in article content")
            else:
                logger.warning("Failed to upload image to Fotolife")
        else:
            logger.warning("Failed to fetch featured image from Unsplash")
    else:
        logger.info("No tags found for image search, skipping featured image")

    # Publish to Hatena Blog
    return publish_to_hatena(
        article_with_image,
        title=title,
        hatena_id=hatena_id,
        blog_id=blog_id,
        api_key=api_key,
        endpoint=endpoint,
        categories=categories,
        draft=draft,
        content_type=content_type,
        timeout=timeout,
    )
