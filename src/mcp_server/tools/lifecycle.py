from typing import Optional
from src.mcp_server import session


def browser_start(mode: str = "cdp", proxy: Optional[str] = None) -> dict:
    """Start browser session. mode: cdp | uc | standard. proxy: optional proxy URL."""
    return session.start(mode=mode, proxy=proxy)


def browser_status() -> dict:
    """Return session status: running | stopped | disconnected, plus current URL."""
    return session.status()


def browser_close() -> dict:
    """Close the browser session and release resources."""
    return session.close()
