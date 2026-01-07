"""Publish articles to Hatena Blog via AtomPub."""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)

NS_ATOM = "http://www.w3.org/2005/Atom"
NS_APP = "http://www.w3.org/2007/app"

ET.register_namespace("", NS_ATOM)
ET.register_namespace("app", NS_APP)


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

    publish_title = title or os.getenv("HATENA_TITLE") or "newsbot"

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
