"""Tests for Hatena Fotolife uploader"""

import pytest
import requests
from io import BytesIO
from unittest.mock import Mock, patch
from src.utils.hatena_fotolife import HatenaFotolifeUploader


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("HATENA_OAUTH_CONSUMER_KEY", "test_key")
    monkeypatch.setenv("HATENA_OAUTH_CONSUMER_SECRET", "test_secret")
    monkeypatch.setenv("HATENA_OAUTH_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("HATENA_OAUTH_ACCESS_TOKEN_SECRET", "test_token_secret")


def test_uploader_initialization(mock_env):
    """Test uploader initializes with env vars"""
    uploader = HatenaFotolifeUploader()
    assert uploader.consumer_key == "test_key"
    assert uploader.consumer_secret == "test_secret"
    assert uploader.access_token == "test_token"
    assert uploader.access_token_secret == "test_token_secret"


def test_uploader_initialization_with_params():
    """Test uploader initializes with explicit parameters"""
    uploader = HatenaFotolifeUploader(
        consumer_key="explicit_key",
        consumer_secret="explicit_secret",
        access_token="explicit_token",
        access_token_secret="explicit_token_secret",
        folder="Test Folder"
    )
    assert uploader.consumer_key == "explicit_key"
    assert uploader.consumer_secret == "explicit_secret"
    assert uploader.access_token == "explicit_token"
    assert uploader.access_token_secret == "explicit_token_secret"
    assert uploader.folder == "Test Folder"


def test_create_upload_xml(mock_env):
    """Test XML creation for upload"""
    uploader = HatenaFotolifeUploader()
    xml = uploader._create_upload_xml("Test Image", b"fake_image_data")

    assert b"<title>Test Image</title>" in xml
    assert b"mode=\"base64\"" in xml
    assert b"type=\"image/jpeg\"" in xml
    assert b"Hatena Blog" in xml  # Default folder name


def test_create_upload_xml_custom_folder(mock_env):
    """Test XML creation with custom folder"""
    uploader = HatenaFotolifeUploader(folder="Custom Folder")
    xml = uploader._create_upload_xml("Test Image", b"fake_image_data")

    assert b"Custom Folder" in xml


def test_extract_image_url_with_syntax(mock_env):
    """Test extraction of hatena:syntax from response"""
    uploader = HatenaFotolifeUploader()

    response_xml = """<?xml version="1.0" encoding="utf-8"?>
    <entry xmlns="http://www.w3.org/2005/Atom" xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#">
        <hatena:syntax>[f:id:testuser:20240101120000j:image]</hatena:syntax>
    </entry>"""

    result = uploader._extract_image_info(response_xml)
    assert result["syntax"] == "[f:id:testuser:20240101120000j:image]"


def test_extract_image_url_with_link(mock_env):
    """Test extraction from link element as fallback"""
    uploader = HatenaFotolifeUploader()

    response_xml = """<?xml version="1.0" encoding="utf-8"?>
    <entry xmlns="http://www.w3.org/2005/Atom">
        <link rel="alternate" href="https://cdn.example.com/image.jpg" />
    </entry>"""

    result = uploader._extract_image_info(response_xml)
    assert result["url"] == "https://cdn.example.com/image.jpg"


def test_extract_image_url_invalid_xml(mock_env):
    """Test handling of invalid XML response"""
    uploader = HatenaFotolifeUploader()

    result = uploader._extract_image_info("invalid xml")
    assert result is None


@patch('src.utils.hatena_fotolife.requests.post')
def test_upload_success(mock_post, mock_env):
    """Test successful image upload"""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.text = """<?xml version="1.0" encoding="utf-8"?>
    <entry xmlns="http://www.w3.org/2005/Atom" xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#">
        <hatena:syntax>[f:id:testuser:20240101120000j:image]</hatena:syntax>
    </entry>"""
    mock_post.return_value = mock_response

    uploader = HatenaFotolifeUploader()
    image_data = BytesIO(b"fake_image")

    result = uploader.upload_image(image_data, "test.jpg", "Test Image")

    assert result["syntax"] == "[f:id:testuser:20240101120000j:image]"
    assert mock_post.called


@patch('src.utils.hatena_fotolife.requests.post')
def test_upload_failure(mock_post, mock_env):
    """Test upload failure handling"""
    mock_post.side_effect = requests.exceptions.RequestException("Network error")

    uploader = HatenaFotolifeUploader()
    image_data = BytesIO(b"fake_image")

    result = uploader.upload_image(image_data, "test.jpg")

    assert result is None


def test_upload_missing_credentials():
    """Test upload fails gracefully without credentials"""
    uploader = HatenaFotolifeUploader(
        consumer_key=None,
        consumer_secret=None,
        access_token=None,
        access_token_secret=None
    )

    image_data = BytesIO(b"fake_image")
    result = uploader.upload_image(image_data, "test.jpg")

    assert result is None


@patch('src.utils.hatena_fotolife.requests.post')
def test_upload_http_error(mock_post, mock_env):
    """Test handling of HTTP errors"""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mock_post.return_value = mock_response

    uploader = HatenaFotolifeUploader()
    image_data = BytesIO(b"fake_image")

    result = uploader.upload_image(image_data, "test.jpg")

    assert result is None
