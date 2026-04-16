from src.mcp_server import session


def browser_click(selector: str) -> dict:
    """Click element by CSS selector. Returns new URL or click confirmation."""
    return session.click(selector)


def browser_type(selector: str, text: str) -> dict:
    """Type text into element by CSS selector."""
    return session.type_text(selector, text)


def browser_scroll(direction: str, amount: int = 300) -> dict:
    """Scroll page. direction: up | down. amount: pixels (default 300)."""
    return session.scroll(direction, amount)


def browser_execute_js(code: str) -> str:
    """Execute JavaScript in page context. Returns result as string."""
    return session.execute_js(code)
