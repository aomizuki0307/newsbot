"""Tests for WordPress publishing module"""

import base64
import pytest
from unittest.mock import Mock, patch

from src.publish_wordpress import WordPressPublisher, publish_to_wordpress


@pytest.fixture
def wp_publisher():
    """WordPressPublisher fixture"""
    return WordPressPublisher(
        site_url='https://example.com',
        username='testuser',
        app_password='test-password'
    )


def test_wordpress_publisher_initialization(wp_publisher):
    """Test WordPressPublisher initialization"""
    assert wp_publisher.site_url == 'https://example.com'
    assert wp_publisher.api_url == 'https://example.com/wp-json/wp/v2/posts'
    assert wp_publisher.username == 'testuser'
    assert wp_publisher.app_password == 'test-password'

    # Check authorization header
    expected_token = base64.b64encode(b'testuser:test-password').decode()
    assert wp_publisher.headers['Authorization'] == f'Basic {expected_token}'
    assert wp_publisher.headers['Content-Type'] == 'application/json'


def test_wordpress_publisher_strips_trailing_slash():
    """Test that WordPressPublisher strips trailing slashes from URLs"""
    publisher = WordPressPublisher(
        site_url='https://example.com/',
        username='user',
        app_password='pass'
    )
    assert publisher.site_url == 'https://example.com'
    assert publisher.api_url == 'https://example.com/wp-json/wp/v2/posts'


@patch('src.publish_wordpress.requests.post')
def test_publish_draft_creates_correct_request(mock_post, wp_publisher):
    """Test that publish_draft creates the correct API request"""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {
        'id': 123,
        'link': 'https://example.com/draft-post',
        'status': 'draft'
    }
    mock_post.return_value = mock_response

    title = "テスト記事"
    content = "# テスト記事\n\nこれはテストです。"

    result = wp_publisher.publish_draft(title, content)

    # Verify requests.post was called with correct parameters
    mock_post.assert_called_once()
    call_args = mock_post.call_args

    # Check URL
    assert call_args[0][0] == 'https://example.com/wp-json/wp/v2/posts'

    # Check headers
    assert call_args[1]['headers'] == wp_publisher.headers

    # Check JSON payload
    json_data = call_args[1]['json']
    assert json_data['title'] == title
    assert json_data['content'] == content
    assert json_data['status'] == 'draft'

    # Check timeout
    assert call_args[1]['timeout'] == 30

    # Check result
    assert result['id'] == 123
    assert result['url'] == 'https://example.com/draft-post'
    assert result['status'] == 'draft'


@patch('src.publish_wordpress.requests.post')
def test_publish_draft_handles_api_errors(mock_post, wp_publisher):
    """Test that publish_draft handles API errors appropriately"""
    # Mock failed response
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_post.return_value = mock_response

    with pytest.raises(Exception, match="API Error"):
        wp_publisher.publish_draft("Title", "Content")


def test_publish_to_wordpress_extracts_title_from_markdown():
    """Test that publish_to_wordpress extracts title from markdown"""
    article = """## Python 3.11の新機能

これは本文です。

### セクション1
内容"""

    with patch('src.publish_wordpress.WordPressPublisher.publish_draft') as mock_publish:
        mock_publish.return_value = {'id': 1, 'url': 'http://example.com', 'status': 'draft'}

        publish_to_wordpress(
            article=article,
            wp_url='https://example.com',
            wp_username='user',
            wp_password='pass'
        )

        # Check that the extracted title is correct
        call_args = mock_publish.call_args
        assert call_args[0][0] == 'Python 3.11の新機能'
        assert call_args[0][1] == article


def test_publish_to_wordpress_uses_default_title_when_no_heading():
    """Test that publish_to_wordpress uses default title when no heading found"""
    article = "これは見出しのない記事です。"

    with patch('src.publish_wordpress.WordPressPublisher.publish_draft') as mock_publish:
        mock_publish.return_value = {'id': 1, 'url': 'http://example.com', 'status': 'draft'}

        publish_to_wordpress(
            article=article,
            wp_url='https://example.com',
            wp_username='user',
            wp_password='pass'
        )

        # Check that default title is used
        call_args = mock_publish.call_args
        assert call_args[0][0] == '技術ニュース記事'


@patch('src.publish_wordpress.requests.post')
def test_publish_draft_request_format(mock_post):
    """Test the exact format of the WordPress API request"""
    publisher = WordPressPublisher(
        site_url='https://test.com',
        username='admin',
        app_password='secret123'
    )

    mock_response = Mock()
    mock_response.json.return_value = {
        'id': 456,
        'link': 'https://test.com/post-456',
        'status': 'draft'
    }
    mock_post.return_value = mock_response

    publisher.publish_draft('My Title', 'My Content')

    # Get the actual call
    _, kwargs = mock_post.call_args

    # Verify exact structure
    assert kwargs['json'] == {
        'title': 'My Title',
        'content': 'My Content',
        'status': 'draft'
    }

    # Verify headers contain auth
    assert 'Authorization' in kwargs['headers']
    assert kwargs['headers']['Authorization'].startswith('Basic ')
    assert kwargs['headers']['Content-Type'] == 'application/json'
