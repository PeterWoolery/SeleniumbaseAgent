import pytest
from unittest.mock import patch
from src.mcp_server.tools.interaction import (
    browser_click, browser_type, browser_scroll, browser_execute_js
)


def test_browser_click():
    with patch("src.mcp_server.tools.interaction.session") as mock_session:
        mock_session.click.return_value = {"status": "clicked", "url": "https://x.com"}
        result = browser_click("button#submit")
    mock_session.click.assert_called_once_with("button#submit")
    assert result["status"] == "clicked"


def test_browser_type():
    with patch("src.mcp_server.tools.interaction.session") as mock_session:
        mock_session.type_text.return_value = {"status": "typed"}
        result = browser_type("input#search", "hello")
    mock_session.type_text.assert_called_once_with("input#search", "hello")
    assert result["status"] == "typed"


def test_browser_scroll_down():
    with patch("src.mcp_server.tools.interaction.session") as mock_session:
        mock_session.scroll.return_value = {"status": "scrolled", "direction": "down", "amount": 300}
        result = browser_scroll("down")
    mock_session.scroll.assert_called_once_with("down", 300)


def test_browser_scroll_custom_amount():
    with patch("src.mcp_server.tools.interaction.session") as mock_session:
        mock_session.scroll.return_value = {"status": "scrolled", "direction": "up", "amount": 500}
        browser_scroll("up", amount=500)
    mock_session.scroll.assert_called_once_with("up", 500)


def test_browser_execute_js():
    with patch("src.mcp_server.tools.interaction.session") as mock_session:
        mock_session.execute_js.return_value = "42"
        result = browser_execute_js("return 6 * 7")
    mock_session.execute_js.assert_called_once_with("return 6 * 7")
    assert result == "42"
