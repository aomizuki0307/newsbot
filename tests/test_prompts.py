"""Tests for prompt loading utilities."""

import pytest

from src import prompts


@pytest.fixture(autouse=True)
def clear_prompt_cache():
    """Ensure cached prompts do not leak across tests."""
    prompts.load_prompt.cache_clear()
    yield
    prompts.load_prompt.cache_clear()


def test_load_prompt_reads_default_variant(tmp_path, monkeypatch):
    """load_prompt should read files relative to PROMPTS_ROOT."""
    monkeypatch.setattr(prompts, "PROMPTS_ROOT", tmp_path)
    target = tmp_path / "default"
    target.mkdir(parents=True)
    (target / "default_summarize_system.txt").write_text("system prompt", encoding="utf-8")

    result = prompts.load_prompt("summarize/system")
    assert result == "system prompt"


def test_load_prompt_falls_back_to_default(monkeypatch, tmp_path):
    """Missing variant should fall back to default text."""
    monkeypatch.setattr(prompts, "PROMPTS_ROOT", tmp_path)
    monkeypatch.setenv("PROMPT_VARIANT", "beta")
    target = tmp_path / "default"
    target.mkdir(parents=True)
    (target / "default_compose_user.txt").write_text("default prompt", encoding="utf-8")

    result = prompts.load_prompt("compose/user")
    assert result == "default prompt"


def test_render_prompt_escapes_braces():
    """render_prompt should escape braces in inserted values."""
    template = "Value: {value}"
    rendered = prompts.render_prompt(template, value="{example}")

    assert rendered == "Value: {example}"
