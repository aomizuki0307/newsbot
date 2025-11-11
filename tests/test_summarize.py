"""Tests for summarize module"""

import pytest
from unittest.mock import Mock, patch

from src.summarize import LLMClient, summarize_article, summarize_articles


@pytest.fixture
def mock_llm_client():
    """Mock LLM client fixture"""
    client = Mock(spec=LLMClient)
    client.generate.return_value = """- Python 3.11がリリースされ、パフォーマンスが大幅に向上
- 新しいエラーメッセージ機能により、デバッグが容易に
- asyncioの改善により非同期処理が高速化
- 型ヒントの機能が拡張され、より厳密な型チェックが可能
- セキュリティアップデートが含まれ、脆弱性が修正"""
    return client


@pytest.fixture
def sample_article():
    """Sample article fixture"""
    return {
        'title': 'Python 3.11 Released with Major Performance Improvements',
        'url': 'https://example.com/python-3.11',
        'text': 'Python 3.11 has been released with significant performance improvements...'
    }


def test_summarize_article_returns_correct_structure(mock_llm_client, sample_article):
    """Test that summarize_article returns the correct dictionary structure"""
    result = summarize_article(sample_article, mock_llm_client)

    # Check structure
    assert isinstance(result, dict)
    assert 'title' in result
    assert 'url' in result
    assert 'summary' in result

    # Check types
    assert isinstance(result['title'], str)
    assert isinstance(result['url'], str)
    assert isinstance(result['summary'], list)


def test_summarize_article_extracts_five_points(mock_llm_client, sample_article):
    """Test that summarize_article extracts exactly 5 summary points"""
    result = summarize_article(sample_article, mock_llm_client)

    # Should have 5 points
    assert len(result['summary']) == 5

    # Each point should be a non-empty string
    for point in result['summary']:
        assert isinstance(point, str)
        assert len(point) > 0


def test_summarize_article_preserves_article_metadata(mock_llm_client, sample_article):
    """Test that summarize_article preserves original article metadata"""
    result = summarize_article(sample_article, mock_llm_client)

    assert result['title'] == sample_article['title']
    assert result['url'] == sample_article['url']


def test_summarize_article_calls_llm_with_correct_prompts(mock_llm_client, sample_article):
    """Test that summarize_article calls LLM with appropriate prompts"""
    summarize_article(sample_article, mock_llm_client)

    # Verify LLM was called once
    mock_llm_client.generate.assert_called_once()

    # Get the call arguments
    call_args = mock_llm_client.generate.call_args
    system_prompt = call_args[0][0]
    user_prompt = call_args[0][1]

    # Verify system prompt contains key instructions
    assert '日本語' in system_prompt
    assert '要約' in system_prompt

    # Verify user prompt contains article info
    assert sample_article['title'] in user_prompt
    assert '5つ' in user_prompt or '5' in user_prompt


def test_summarize_article_handles_malformed_response(sample_article):
    """Test that summarize_article handles malformed LLM responses gracefully"""
    mock_client = Mock(spec=LLMClient)
    mock_client.generate.return_value = "This is not a bulleted list"

    result = summarize_article(sample_article, mock_client)

    # Should still return valid structure
    assert isinstance(result, dict)
    assert 'summary' in result
    assert isinstance(result['summary'], list)
    assert len(result['summary']) > 0


@patch('src.summarize.OpenAI')
def test_llm_client_openai_initialization(mock_openai_class):
    """Test LLMClient initialization with OpenAI provider"""
    with patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test-key',
        'OPENAI_MODEL': 'gpt-4'
    }):
        client = LLMClient(provider='openai')

        assert client.provider == 'openai'
        assert client.model == 'gpt-4'
        mock_openai_class.assert_called_once()


@patch('src.summarize.Anthropic')
def test_llm_client_anthropic_initialization(mock_anthropic_class):
    """Test LLMClient initialization with Anthropic provider"""
    with patch.dict('os.environ', {
        'ANTHROPIC_API_KEY': 'test-key',
        'ANTHROPIC_MODEL': 'claude-3-sonnet'
    }):
        client = LLMClient(provider='anthropic')

        assert client.provider == 'anthropic'
        assert client.model == 'claude-3-sonnet'
        mock_anthropic_class.assert_called_once()


def test_llm_client_invalid_provider_raises_error():
    """Test that LLMClient raises error for invalid provider"""
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMClient(provider='invalid-provider')


def test_summarize_articles_enforces_token_budget(monkeypatch):
    """summarize_articles should stop scheduling when token budget is exceeded."""

    class DummyClient:
        def __init__(self, provider='openai'):
            self.provider = provider

    def fake_summarize(article, _client):
        return {'title': article['title'], 'url': article['url'], 'summary': ['ok']}

    monkeypatch.setattr('src.summarize.LLMClient', DummyClient)
    monkeypatch.setattr('src.summarize.summarize_article', fake_summarize)

    articles = [
        {'title': f'Article {i}', 'url': f'https://example.com/{i}', 'text': 'x' * 800}
        for i in range(3)
    ]

    result = summarize_articles(articles, provider='openai', max_tokens=600)

    assert len(result.summaries) == 1
    assert result.limit_reached
    assert result.skipped_due_to_budget >= 2


def test_summarize_articles_counts_failures(monkeypatch):
    """summarize_articles should continue when individual articles fail."""

    class DummyClient:
        def __init__(self, provider='openai'):
            self.provider = provider

    def fake_summarize(article, _client):
        if article['title'] == 'Bad':
            raise ValueError("LLM error")
        return {'title': article['title'], 'url': article['url'], 'summary': ['ok']}

    monkeypatch.setattr('src.summarize.LLMClient', DummyClient)
    monkeypatch.setattr('src.summarize.summarize_article', fake_summarize)

    articles = [
        {'title': 'Good', 'url': 'https://example.com/1', 'text': 'data' * 100},
        {'title': 'Bad', 'url': 'https://example.com/2', 'text': 'data' * 100},
        {'title': 'Good2', 'url': 'https://example.com/3', 'text': 'data' * 100},
    ]

    result = summarize_articles(articles, provider='openai')

    assert len(result.summaries) == 2
    assert result.failed == 1
