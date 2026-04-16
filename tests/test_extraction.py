import pytest
from unittest.mock import patch
from src.mcp_server.tools.extraction import browser_get_text, browser_get_links, browser_screenshot


def test_browser_get_text_no_selector():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_text.return_value = "Page content"
        result = browser_get_text()
    mock_session.get_text.assert_called_once_with(selector=None)
    assert result == "Page content"


def test_browser_get_text_with_selector():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_text.return_value = "Section content"
        result = browser_get_text(selector="#main")
    mock_session.get_text.assert_called_once_with(selector="#main")
    assert result == "Section content"


def test_browser_get_links_no_filter():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_links.return_value = [{"text": "Home", "href": "https://x.com"}]
        result = browser_get_links()
    mock_session.get_links.assert_called_once_with(filter_str=None)
    assert result[0]["text"] == "Home"


def test_browser_get_links_with_filter():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_links.return_value = []
        browser_get_links(filter="github.com")
    mock_session.get_links.assert_called_once_with(filter_str="github.com")


def test_browser_screenshot():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.screenshot.return_value = "base64data=="
        result = browser_screenshot()
    mock_session.screenshot.assert_called_once()
    assert result == "base64data=="
