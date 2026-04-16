import pytest
from unittest.mock import patch
from src.mcp_server.tools.captcha import browser_solve_captcha


def test_solve_captcha_delegates():
    with patch("src.mcp_server.tools.captcha.session") as mock_session:
        mock_session.solve_captcha.return_value = {"status": "attempted", "method": "cdp_solve_captcha"}
        result = browser_solve_captcha()
    mock_session.solve_captcha.assert_called_once()
    assert result["status"] == "attempted"
