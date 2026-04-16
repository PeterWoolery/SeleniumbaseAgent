import pytest
from unittest.mock import patch
from src.mcp_server.tools.lifecycle import browser_start, browser_status, browser_close


def test_browser_start_delegates_to_session():
    with patch("src.mcp_server.tools.lifecycle.session") as mock_session:
        mock_session.start.return_value = {"status": "running", "mode": "cdp"}
        result = browser_start(mode="cdp", proxy=None)
    mock_session.start.assert_called_once_with(mode="cdp", proxy=None)
    assert result["status"] == "running"


def test_browser_start_default_mode():
    with patch("src.mcp_server.tools.lifecycle.session") as mock_session:
        mock_session.start.return_value = {"status": "running", "mode": "cdp"}
        browser_start()
    mock_session.start.assert_called_once_with(mode="cdp", proxy=None)


def test_browser_status_delegates():
    with patch("src.mcp_server.tools.lifecycle.session") as mock_session:
        mock_session.status.return_value = {"status": "running", "url": "https://x.com"}
        result = browser_status()
    assert result["status"] == "running"


def test_browser_close_delegates():
    with patch("src.mcp_server.tools.lifecycle.session") as mock_session:
        mock_session.close.return_value = {"status": "closed"}
        result = browser_close()
    assert result["status"] == "closed"
