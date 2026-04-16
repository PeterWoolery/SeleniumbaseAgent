# tests/test_navigation.py
import pytest
from unittest.mock import patch
from src.mcp_server.tools.navigation import browser_navigate, browser_back


def test_browser_navigate_delegates():
    with patch("src.mcp_server.tools.navigation.session") as mock_session:
        mock_session.navigate.return_value = {
            "title": "Example",
            "url": "https://example.com",
            "text": "Hello world",
        }
        result = browser_navigate("https://example.com")
    mock_session.navigate.assert_called_once_with("https://example.com")
    assert result["title"] == "Example"
    assert result["url"] == "https://example.com"


def test_browser_back_delegates():
    with patch("src.mcp_server.tools.navigation.session") as mock_session:
        mock_session.back.return_value = {"url": "https://prev.com", "text": "Prev"}
        result = browser_back()
    mock_session.back.assert_called_once()
    assert result["url"] == "https://prev.com"
