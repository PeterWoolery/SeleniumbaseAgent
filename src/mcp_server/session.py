# src/mcp_server/session.py
import base64
import os
import threading
from dataclasses import dataclass
from typing import Optional

import html2text
from seleniumbase import SB


@dataclass
class _State:
    sb: Optional[object] = None
    mode: str = "cdp"
    status: str = "stopped"   # stopped | running | disconnected
    current_url: str = ""


_state = _State()
_lock = threading.Lock()
_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "30"))


def _reset() -> None:
    """Reset to initial state (test helper, also called by close)."""
    global _state
    _state = _State()


def _require_session() -> object:
    if _state.status != "running" or _state.sb is None:
        raise RuntimeError("No active session. Call browser_start first.")
    return _state.sb


def _html_to_markdown(html: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    return h.handle(html).strip()


def _page_text(sb) -> str:
    try:
        html = sb.get_page_source()
    except Exception:
        html = sb.execute_script("return document.documentElement.outerHTML")
    return _html_to_markdown(html)


# ── Session lifecycle ──────────────────────────────────────────────────────────

def start(mode: str = "cdp", proxy: Optional[str] = None) -> dict:
    """Start a browser session. mode: cdp | uc | standard."""
    with _lock:
        if _state.status == "running":
            return {"status": "already_running", "url": _state.current_url}

        kwargs = dict(
            uc=True,
            xvfb=not bool(os.getenv("DISPLAY")),
            headless=False,
            timeout=_TIMEOUT,
        )
        if proxy:
            kwargs["proxy"] = proxy

        sb = SB(**kwargs)
        sb.__enter__()

        _state.sb = sb
        _state.mode = mode
        _state.status = "running"
        _state.current_url = ""

        return {"status": "running", "mode": mode}


def close() -> dict:
    """Close the browser session."""
    with _lock:
        if _state.sb is not None:
            try:
                _state.sb.__exit__(None, None, None)
            except Exception:
                pass
        _reset()
        return {"status": "closed"}


def status() -> dict:
    """Return current session status."""
    try:
        url = _state.sb.get_current_url() if _state.status == "running" else ""
    except Exception:
        url = _state.current_url
    return {"status": _state.status, "url": url, "mode": _state.mode}


# ── Navigation ─────────────────────────────────────────────────────────────────

def navigate(url: str) -> dict:
    """Navigate to URL. Returns title, cleaned text, final URL."""
    with _lock:
        sb = _require_session()
        if _state.mode == "cdp":
            sb.activate_cdp_mode(url)
        elif _state.mode == "uc":
            sb.uc_open_with_reconnect(url, 4)
        else:
            sb.open(url)
        current = sb.get_current_url()
        _state.current_url = current
        return {
            "title": sb.get_title(),
            "url": current,
            "text": _page_text(sb),
        }


def back() -> dict:
    """Navigate back one page."""
    with _lock:
        sb = _require_session()
        sb.go_back()
        current = sb.get_current_url()
        _state.current_url = current
        return {"url": current, "text": _page_text(sb)}


# ── Extraction ─────────────────────────────────────────────────────────────────

def get_text(selector: Optional[str] = None) -> str:
    """Return Markdown-cleaned text of element or full page."""
    with _lock:
        sb = _require_session()
        if selector:
            element = sb.find_element(selector)
            return element.get_attribute("innerHTML") or element.text
        return _page_text(sb)


def get_links(filter_str: Optional[str] = None) -> list[dict]:
    """Return list of {text, href} links, optionally filtered by domain/pattern."""
    with _lock:
        sb = _require_session()
        elements = sb.find_elements("a")
        links = []
        for el in elements:
            href = el.get_attribute("href") or ""
            text = el.text.strip()
            if not href:
                continue
            if filter_str and filter_str not in href:
                continue
            links.append({"text": text, "href": href})
        return links


def screenshot() -> str:
    """Return base64-encoded PNG of current page."""
    with _lock:
        sb = _require_session()
        png = sb.driver.get_screenshot_as_png()
        return base64.b64encode(png).decode("utf-8")


# ── Interaction ────────────────────────────────────────────────────────────────

def click(selector: str) -> dict:
    """Click an element by CSS selector."""
    with _lock:
        sb = _require_session()
        sb.click(selector)
        current = sb.get_current_url()
        _state.current_url = current
        return {"status": "clicked", "url": current}


def type_text(selector: str, text: str) -> dict:
    """Type text into an element by CSS selector."""
    with _lock:
        sb = _require_session()
        sb.type(selector, text)
        return {"status": "typed"}


def scroll(direction: str, amount: int = 300) -> dict:
    """Scroll the page up or down by pixel amount."""
    with _lock:
        sb = _require_session()
        px = amount if direction == "down" else -amount
        sb.execute_script(f"window.scrollBy(0, {px})")
        return {"status": "scrolled", "direction": direction, "amount": amount}


def execute_js(code: str) -> str:
    """Execute JavaScript and return result as string."""
    with _lock:
        sb = _require_session()
        result = sb.execute_script(code)
        return str(result)


# ── CAPTCHA ────────────────────────────────────────────────────────────────────

def solve_captcha() -> dict:
    """Attempt CAPTCHA solving using mode-appropriate method."""
    with _lock:
        sb = _require_session()
        if _state.mode == "cdp":
            sb.solve_captcha()
            return {"status": "attempted", "method": "cdp_solve_captcha"}
        elif _state.mode == "uc":
            sb.uc_gui_click_captcha()
            return {"status": "attempted", "method": "uc_gui_click_captcha"}
        else:
            return {"status": "skipped", "reason": "standard mode has no CAPTCHA solver"}
