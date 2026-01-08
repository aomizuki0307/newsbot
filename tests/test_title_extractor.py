"""Tests for title extraction utilities"""

import pytest
from src.utils.title_extractor import (
    extract_title_from_html,
    extract_title_from_markdown,
    extract_title,
)


def test_extract_html_h1():
    """Test extraction from HTML h1 tag"""
    content = "<h1>テストタイトル</h1><p>本文</p>"
    assert extract_title_from_html(content) == "テストタイトル"


def test_extract_html_h2():
    """Test extraction from HTML h2 tag"""
    content = "<h2>サブタイトル</h2><p>本文</p>"
    assert extract_title_from_html(content) == "サブタイトル"


def test_extract_html_multiple_headers():
    """Test extraction picks first header"""
    content = "<h2>最初のタイトル</h2><p>本文</p><h2>次のタイトル</h2>"
    assert extract_title_from_html(content) == "最初のタイトル"


def test_extract_html_no_header():
    """Test fallback when no header found"""
    content = "<p>本文のみ</p>"
    assert extract_title_from_html(content, default="デフォルト") == "デフォルト"


def test_extract_html_real_example():
    """Test with real example from Hatena post"""
    content = "<h2>テンプレートとは：マーケティングカレンダーでの役割</h2><p>日々の投稿や地域のお知らせ...</p>"
    assert extract_title_from_html(content) == "テンプレートとは：マーケティングカレンダーでの役割"


def test_extract_markdown_h1():
    """Test extraction from markdown h1"""
    content = "# Markdown Title\n\nBody text"
    assert extract_title_from_markdown(content) == "Markdown Title"


def test_extract_markdown_h2():
    """Test extraction from markdown h2"""
    content = "## Markdown Subtitle\n\nBody text"
    assert extract_title_from_markdown(content) == "Markdown Subtitle"


def test_extract_markdown_no_header():
    """Test fallback when no markdown header found"""
    content = "Just plain text"
    assert extract_title_from_markdown(content, default="デフォルト") == "デフォルト"


def test_extract_smart_html():
    """Test smart extraction detects HTML"""
    content = "<h2>HTMLタイトル</h2><p>本文</p>"
    assert extract_title(content) == "HTMLタイトル"


def test_extract_smart_markdown():
    """Test smart extraction detects Markdown"""
    content = "# Markdown Title\n\nBody text"
    assert extract_title(content) == "Markdown Title"


def test_extract_long_title_truncation():
    """Test title truncation to 100 characters"""
    long_title = "あ" * 150
    content = f"<h1>{long_title}</h1>"
    result = extract_title_from_html(content)
    assert len(result) == 100


def test_extract_with_whitespace():
    """Test extraction handles extra whitespace"""
    content = "<h2>  Whitespace Title  </h2>"
    assert extract_title_from_html(content) == "Whitespace Title"


def test_extract_empty_header():
    """Test extraction with empty header tag"""
    content = "<h2></h2><p>Body</p>"
    assert extract_title_from_html(content, default="Empty") == "Empty"
