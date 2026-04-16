# src/mcp_server/tools/navigation.py
from src.mcp_server import session


def browser_navigate(url: str) -> dict:
    """Navigate to URL. Returns title, Markdown-cleaned page text, final URL."""
    return session.navigate(url)


def browser_back() -> dict:
    """Navigate back one page. Returns new URL and page text."""
    return session.back()
