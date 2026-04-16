from typing import Optional
from src.mcp_server import session


def browser_get_text(selector: Optional[str] = None) -> str:
    """Get Markdown-cleaned text. selector: CSS selector for element, or None for full page."""
    return session.get_text(selector=selector)


def browser_get_links(filter: Optional[str] = None) -> list[dict]:
    """Get all links as [{text, href}]. filter: optional domain/string to filter hrefs."""
    return session.get_links(filter_str=filter)


def browser_screenshot() -> str:
    """Capture current page as base64-encoded PNG."""
    return session.screenshot()
