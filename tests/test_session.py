# tests/test_session.py
import pytest
from unittest.mock import MagicMock, patch
import src.mcp_server.session as session_module


@pytest.fixture(autouse=True)
def reset_session():
    """Reset session state before each test."""
    session_module._reset()
    yield
    session_module._reset()


def _make_mock_sb():
    sb = MagicMock()
    sb.__enter__ = MagicMock(return_value=sb)
    sb.__exit__ = MagicMock(return_value=False)
    sb.get_current_url.return_value = "about:blank"
    sb.get_title.return_value = ""
    sb.get_page_source.return_value = "<html><body></body></html>"
    return sb


def test_start_returns_running():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        result = session_module.start(mode="standard")
    assert result["status"] == "running"
    assert result["mode"] == "standard"


def test_start_already_running():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="standard")
        result = session_module.start(mode="standard")
    assert result["status"] == "already_running"


def test_status_stopped_initially():
    result = session_module.status()
    assert result["status"] == "stopped"


def test_status_running_after_start():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="cdp")
        result = session_module.status()
    assert result["status"] == "running"


def test_close_stops_session():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="standard")
        result = session_module.close()
    assert result["status"] == "closed"
    assert session_module.status()["status"] == "stopped"


def test_close_calls_sb_exit():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="standard")
        session_module.close()
    mock_sb.__exit__.assert_called_once_with(None, None, None)


def test_navigate_standard_mode():
    mock_sb = _make_mock_sb()
    mock_sb.get_current_url.return_value = "https://example.com"
    mock_sb.get_title.return_value = "Example"
    mock_sb.get_page_source.return_value = "<html><body><p>Hello world</p></body></html>"
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="standard")
        result = session_module.navigate("https://example.com")
    mock_sb.open.assert_called_once_with("https://example.com")
    assert result["title"] == "Example"
    assert result["url"] == "https://example.com"
    assert "Hello world" in result["text"]


def test_navigate_uc_mode():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="uc")
        session_module.navigate("https://example.com")
    mock_sb.uc_open_with_reconnect.assert_called_once_with("https://example.com", 4)


def test_navigate_cdp_mode():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb):
        session_module.start(mode="cdp")
        session_module.navigate("https://example.com")
    mock_sb.activate_cdp_mode.assert_called_once_with("https://example.com")


def test_navigate_raises_when_no_session():
    with pytest.raises(RuntimeError, match="No active session"):
        session_module.navigate("https://example.com")


def test_proxy_passed_to_sb():
    mock_sb = _make_mock_sb()
    with patch("src.mcp_server.session.SB", return_value=mock_sb) as MockSB:
        session_module.start(mode="standard", proxy="http://proxy:8080")
    MockSB.assert_called_once()
    call_kwargs = MockSB.call_args[1]
    assert call_kwargs["proxy"] == "http://proxy:8080"
