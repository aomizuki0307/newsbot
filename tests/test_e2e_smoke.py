"""End-to-end smoke test covering collection through publishing."""

import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest
import responses

from src.collect import ArticleCache, collect_articles
from src.compose import compose_article, save_draft
from src.publish_wordpress import publish_to_wordpress
import src.compose as compose_module
import src.summarize as summarize_module
from src.summarize import SummarizationResult


@responses.activate
def test_e2e_smoke_flow(monkeypatch, tmp_path):
    """Run a smoke test that exercises the primary pipeline surfaces."""
    fixtures_dir = Path("tests/fixtures")
    rss_path = fixtures_dir / "rss.xml"
    article_dir = fixtures_dir / "articles"
    allowlist_path = tmp_path / "allowlist.txt"
    allowlist_path.write_text("example.com\n", encoding="utf-8")

    article_fixtures = {
        "https://example.com/article-1": {
            "title": "Sample Article One",
            "text": (article_dir / "article-1.html").read_text(encoding="utf-8"),
        },
        "https://example.com/article-2": {
            "title": "Sample Article Two",
            "text": (article_dir / "article-2.html").read_text(encoding="utf-8"),
        },
    }

    def fake_feedparser_parse(_feed_url):
        tree = ET.parse(rss_path)
        entries = []
        for item in tree.findall(".//item"):
            entries.append(SimpleNamespace(link=item.findtext("link")))
        return SimpleNamespace(entries=entries, bozo=False)

    monkeypatch.setattr("src.collect.feedparser.parse", fake_feedparser_parse)

    monkeypatch.setattr("src.collect._host_addresses", lambda _host: ["93.184.216.34"])

    class StubArticle:
        def __init__(self, url: str):
            self.url = url
            self.title = ""
            self.text = ""
            self.publish_date = None

        def download(self):
            # Download is skipped; fixtures already contain content.
            pass

        def parse(self):
            data = article_fixtures[self.url]
            self.title = data["title"]
            self.text = data["text"]

    monkeypatch.setattr("src.collect.Article", StubArticle)

    class StubLLMClient:
        def __init__(self, provider: str = "openai"):
            self.provider = provider

        def generate(self, system: str, user: str, temperature: float = 0.7):
            return (
                "## テックニュースまとめ\n\n"
                "### ハイライト\n- Article digest\n\n"
                "### 参考リンク\n- https://example.com/article-1\n- https://example.com/article-2"
            )

    def fake_summarize_articles(articles, provider: str = "openai"):
        summaries = []
        for article in articles:
            summaries.append(
                {
                    "title": article["title"],
                    "url": article["url"],
                    "summary": [f"{article['title']} 要点{i}" for i in range(1, 6)],
                }
            )
        return SummarizationResult(
            summaries=summaries,
            failed=0,
            estimated_tokens=0,
        )

    monkeypatch.setattr("src.summarize.LLMClient", StubLLMClient)
    monkeypatch.setattr(compose_module, "LLMClient", StubLLMClient)
    monkeypatch.setattr(summarize_module, "summarize_articles", fake_summarize_articles)

    cache = ArticleCache(cache_file=str(tmp_path / "cache.json"), duration_hours=1)
    articles = collect_articles(
        ["fixtures://sample-feed"],
        cache,
        allowlist_path=str(allowlist_path),
    )

    assert len(articles) == 2

    summary_result = summarize_module.summarize_articles(articles, provider="openai")
    assert len(summary_result.summaries) == 2

    article_md = compose_article(summary_result.summaries, provider="openai")

    draft_path = tmp_path / "draft.md"
    save_draft(article_md, output_file=str(draft_path))

    responses.add(
        responses.POST,
        "https://wp.example.com/wp-json/wp/v2/posts",
        json={"id": 42, "link": "https://wp.example.com/?p=42", "status": "draft"},
        status=201,
    )

    result = publish_to_wordpress(
        article_md,
        wp_url="https://wp.example.com",
        wp_username="tester",
        wp_password="secret",
    )

    assert result["url"] == "https://wp.example.com/?p=42"
    recorded = json.loads(responses.calls[0].request.body)
    assert recorded["status"] == "draft"
    assert recorded["title"] == "テックニュースまとめ"
    assert "テックニュースまとめ" in draft_path.read_text(encoding="utf-8")
