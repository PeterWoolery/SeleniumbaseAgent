# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sb():
    """Mocked SeleniumBase SB instance."""
    sb = MagicMock()
    sb.get_current_url.return_value = "https://example.com"
    sb.get_title.return_value = "Example Domain"
    sb.get_page_source.return_value = "<html><body><p>Hello</p></body></html>"
    return sb
