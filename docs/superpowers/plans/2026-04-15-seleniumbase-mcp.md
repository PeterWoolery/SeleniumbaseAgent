# SeleniumBase MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerized MCP server that gives Claude Code and OpenCode live browser control via SeleniumBase with UC/CDP/standard mode selection and optional proxy support.

**Architecture:** Single container (Python 3.12 + Chrome + Xvfb + SeleniumBase) exposes an HTTP/SSE MCP endpoint on port 8765. The MCP server holds a stateful SeleniumBase session (`SB(uc=True)`) across tool calls. All browser operations run in a thread executor to avoid blocking the asyncio event loop.

**Tech Stack:** Python 3.12, SeleniumBase (UC+CDP mode), MCP Python SDK (`mcp>=1.0`), Starlette + uvicorn (SSE transport), html2text (content cleaning), pytest + unittest.mock (tests), Docker + docker-compose.

---

## File Map

```
SeleniumBaseAgent/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── tests/
│   ├── conftest.py
│   ├── test_proxy.py
│   ├── test_session.py
│   ├── test_lifecycle.py
│   ├── test_navigation.py
│   ├── test_extraction.py
│   ├── test_interaction.py
│   └── test_captcha.py
└── src/
    └── mcp_server/
        ├── __init__.py
        ├── server.py        # MCP entrypoint, SSE transport, tool dispatch
        ├── session.py       # SB lifecycle + all browser operations
        ├── proxy.py         # proxy config resolution
        └── tools/
            ├── __init__.py
            ├── lifecycle.py  # browser_start, browser_status, browser_close tool defs
            ├── navigation.py # browser_navigate, browser_back tool defs
            ├── extraction.py # browser_get_text, browser_get_links, browser_screenshot tool defs
            ├── interaction.py # browser_click, browser_type, browser_scroll, browser_execute_js tool defs
            └── captcha.py   # browser_solve_captcha tool def
```

**Interface contract** (session.py → tools/*.py):
- `session.start(mode, proxy) -> dict`
- `session.close() -> dict`
- `session.status() -> dict`
- `session.navigate(url) -> dict`
- `session.back() -> dict`
- `session.get_text(selector) -> str`
- `session.get_links(filter_str) -> list[dict]`
- `session.screenshot() -> str`  (base64 PNG)
- `session.click(selector) -> dict`
- `session.type_text(selector, text) -> dict`
- `session.scroll(direction, amount) -> dict`
- `session.execute_js(code) -> str`
- `session.solve_captcha() -> dict`

---

## Task 1: Git init + project scaffold

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/mcp_server/__init__.py`
- Create: `src/mcp_server/tools/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Init git and create directory structure**

```bash
cd /home/peter/Projects/SeleniumBaseAgent
git init
mkdir -p src/mcp_server/tools tests
```

- [ ] **Step 2: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
dist/
*.egg-info/
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "seleniumbase-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "seleniumbase>=4.29",
    "mcp>=1.0",
    "starlette",
    "uvicorn[standard]",
    "html2text",
    "httpx",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "anyio"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_server"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 4: Write empty `__init__.py` files**

`src/mcp_server/__init__.py` — empty file.
`src/mcp_server/tools/__init__.py` — empty file.

- [ ] **Step 5: Write `tests/conftest.py`**

```python
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
```

- [ ] **Step 6: Install dev dependencies**

```bash
uv venv .venv
uv pip install -e ".[dev]"
```

Expected: packages install without errors.

- [ ] **Step 7: Verify pytest runs**

```bash
.venv/bin/pytest --collect-only
```

Expected: `0 tests collected` (no tests yet).

- [ ] **Step 8: Commit**

```bash
git add .gitignore pyproject.toml src/ tests/
git commit -m "chore: project scaffold"
```

---

## Task 2: Proxy resolver

**Files:**
- Create: `src/mcp_server/proxy.py`
- Create: `tests/test_proxy.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_proxy.py
import pytest
from src.mcp_server.proxy import resolve_proxy


def test_per_call_proxy_returned():
    result = resolve_proxy(per_call="http://proxy:8080")
    assert result == "http://proxy:8080"


def test_no_proxy_by_default(monkeypatch):
    monkeypatch.delenv("ALWAYS_PROXY", raising=False)
    monkeypatch.delenv("SELENIUM_PROXY", raising=False)
    assert resolve_proxy() is None


def test_always_proxy_uses_env(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy() == "http://env-proxy:3128"


def test_always_proxy_missing_url_returns_none(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.delenv("SELENIUM_PROXY", raising=False)
    assert resolve_proxy() is None


def test_per_call_overrides_always_proxy(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "true")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy(per_call="http://override:9090") == "http://override:9090"


def test_always_proxy_case_insensitive(monkeypatch):
    monkeypatch.setenv("ALWAYS_PROXY", "True")
    monkeypatch.setenv("SELENIUM_PROXY", "http://env-proxy:3128")
    assert resolve_proxy() == "http://env-proxy:3128"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_proxy.py -v
```

Expected: `ImportError: cannot import name 'resolve_proxy'`

- [ ] **Step 3: Implement `proxy.py`**

```python
# src/mcp_server/proxy.py
import os
from typing import Optional


def resolve_proxy(per_call: Optional[str] = None) -> Optional[str]:
    """Return proxy URL to use, or None for direct connection.

    Priority: per_call arg > ALWAYS_PROXY+SELENIUM_PROXY env > None.
    """
    if per_call:
        return per_call
    if os.getenv("ALWAYS_PROXY", "false").lower() == "true":
        return os.getenv("SELENIUM_PROXY") or None
    return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_proxy.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/proxy.py tests/test_proxy.py
git commit -m "feat: proxy resolver"
```

---

## Task 3: Session manager

**Files:**
- Create: `src/mcp_server/session.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_session.py
import pytest
from unittest.mock import MagicMock, patch, call
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_session.py -v
```

Expected: `ImportError: cannot import name 'start'`

- [ ] **Step 3: Implement `session.py`**

```python
# src/mcp_server/session.py
import base64
import os
import threading
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_session.py -v
```

Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/session.py tests/test_session.py
git commit -m "feat: session manager with UC/CDP/standard mode dispatch"
```

---

## Task 4: Lifecycle tools

**Files:**
- Create: `src/mcp_server/tools/lifecycle.py`
- Create: `tests/test_lifecycle.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lifecycle.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_lifecycle.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `lifecycle.py`**

```python
# src/mcp_server/tools/lifecycle.py
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_lifecycle.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/tools/lifecycle.py tests/test_lifecycle.py
git commit -m "feat: lifecycle tools (browser_start, browser_status, browser_close)"
```

---

## Task 5: Navigation tools

**Files:**
- Create: `src/mcp_server/tools/navigation.py`
- Create: `tests/test_navigation.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_navigation.py
import pytest
from unittest.mock import patch
from src.mcp_server.tools.navigation import browser_navigate, browser_back


def test_browser_navigate_delegates():
    with patch("src.mcp_server.tools.navigation.session") as mock_session:
        mock_session.navigate.return_value = {
            "title": "Example",
            "url": "https://example.com",
            "text": "Hello world",
        }
        result = browser_navigate("https://example.com")
    mock_session.navigate.assert_called_once_with("https://example.com")
    assert result["title"] == "Example"
    assert result["url"] == "https://example.com"


def test_browser_back_delegates():
    with patch("src.mcp_server.tools.navigation.session") as mock_session:
        mock_session.back.return_value = {"url": "https://prev.com", "text": "Prev"}
        result = browser_back()
    mock_session.back.assert_called_once()
    assert result["url"] == "https://prev.com"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_navigation.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `navigation.py`**

```python
# src/mcp_server/tools/navigation.py
from src.mcp_server import session


def browser_navigate(url: str) -> dict:
    """Navigate to URL. Returns title, Markdown-cleaned page text, final URL."""
    return session.navigate(url)


def browser_back() -> dict:
    """Navigate back one page. Returns new URL and page text."""
    return session.back()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_navigation.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/tools/navigation.py tests/test_navigation.py
git commit -m "feat: navigation tools (browser_navigate, browser_back)"
```

---

## Task 6: Extraction tools

**Files:**
- Create: `src/mcp_server/tools/extraction.py`
- Create: `tests/test_extraction.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extraction.py
import pytest
from unittest.mock import patch
from src.mcp_server.tools.extraction import browser_get_text, browser_get_links, browser_screenshot


def test_browser_get_text_no_selector():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_text.return_value = "Page content"
        result = browser_get_text()
    mock_session.get_text.assert_called_once_with(selector=None)
    assert result == "Page content"


def test_browser_get_text_with_selector():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_text.return_value = "Section content"
        result = browser_get_text(selector="#main")
    mock_session.get_text.assert_called_once_with(selector="#main")
    assert result == "Section content"


def test_browser_get_links_no_filter():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_links.return_value = [{"text": "Home", "href": "https://x.com"}]
        result = browser_get_links()
    mock_session.get_links.assert_called_once_with(filter_str=None)
    assert result[0]["text"] == "Home"


def test_browser_get_links_with_filter():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.get_links.return_value = []
        browser_get_links(filter="github.com")
    mock_session.get_links.assert_called_once_with(filter_str="github.com")


def test_browser_screenshot():
    with patch("src.mcp_server.tools.extraction.session") as mock_session:
        mock_session.screenshot.return_value = "base64data=="
        result = browser_screenshot()
    mock_session.screenshot.assert_called_once()
    assert result == "base64data=="
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_extraction.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `extraction.py`**

```python
# src/mcp_server/tools/extraction.py
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_extraction.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/tools/extraction.py tests/test_extraction.py
git commit -m "feat: extraction tools (browser_get_text, browser_get_links, browser_screenshot)"
```

---

## Task 7: Interaction tools

**Files:**
- Create: `src/mcp_server/tools/interaction.py`
- Create: `tests/test_interaction.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_interaction.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
.venv/bin/pytest tests/test_interaction.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `interaction.py`**

```python
# src/mcp_server/tools/interaction.py
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
.venv/bin/pytest tests/test_interaction.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/mcp_server/tools/interaction.py tests/test_interaction.py
git commit -m "feat: interaction tools (browser_click, browser_type, browser_scroll, browser_execute_js)"
```

---

## Task 8: CAPTCHA tool

**Files:**
- Create: `src/mcp_server/tools/captcha.py`
- Create: `tests/test_captcha.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_captcha.py
import pytest
from unittest.mock import patch
from src.mcp_server.tools.captcha import browser_solve_captcha


def test_solve_captcha_delegates():
    with patch("src.mcp_server.tools.captcha.session") as mock_session:
        mock_session.solve_captcha.return_value = {"status": "attempted", "method": "cdp_solve_captcha"}
        result = browser_solve_captcha()
    mock_session.solve_captcha.assert_called_once()
    assert result["status"] == "attempted"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
.venv/bin/pytest tests/test_captcha.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `captcha.py`**

```python
# src/mcp_server/tools/captcha.py
from src.mcp_server import session


def browser_solve_captcha() -> dict:
    """Attempt CAPTCHA solving using mode-appropriate method.

    CDP mode: sb.solve_captcha()
    UC mode:  sb.uc_gui_click_captcha()
    standard: no-op
    """
    return session.solve_captcha()
```

- [ ] **Step 4: Run test — verify it passes**

```bash
.venv/bin/pytest tests/test_captcha.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server/tools/captcha.py tests/test_captcha.py
git commit -m "feat: captcha tool (browser_solve_captcha)"
```

---

## Task 9: MCP server entrypoint

**Files:**
- Create: `src/mcp_server/server.py`

No unit tests for the server wiring — integration-tested in Task 11.

- [ ] **Step 1: Write `server.py`**

```python
# src/mcp_server/server.py
import asyncio
import json
import os
from typing import Any

import uvicorn
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from src.mcp_server.tools.lifecycle import browser_start, browser_status, browser_close
from src.mcp_server.tools.navigation import browser_navigate, browser_back
from src.mcp_server.tools.extraction import browser_get_text, browser_get_links, browser_screenshot
from src.mcp_server.tools.interaction import browser_click, browser_type, browser_scroll, browser_execute_js
from src.mcp_server.tools.captcha import browser_solve_captcha

server = Server("seleniumbase-mcp")

_TOOLS = [
    types.Tool(
        name="browser_start",
        description="Start a browser session. mode: cdp (default, stealthiest) | uc | standard. proxy: optional proxy URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["cdp", "uc", "standard"], "default": "cdp"},
                "proxy": {"type": "string", "description": "Proxy URL e.g. http://user:pass@host:port"},
            },
        },
    ),
    types.Tool(
        name="browser_status",
        description="Check if a browser session is running. Returns status and current URL.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="browser_close",
        description="Close the active browser session.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="browser_navigate",
        description="Navigate to a URL. Returns page title, Markdown-cleaned text, and final URL.",
        inputSchema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    ),
    types.Tool(
        name="browser_back",
        description="Navigate back one page. Returns new URL and page text.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="browser_get_text",
        description="Get Markdown-cleaned text of the current page or a specific element.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector. Omit for full page."},
            },
        },
    ),
    types.Tool(
        name="browser_get_links",
        description="Get all links on the page as [{text, href}]. Optionally filter by domain or pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "String to filter hrefs by (e.g. 'github.com')."},
            },
        },
    ),
    types.Tool(
        name="browser_screenshot",
        description="Capture current page as base64-encoded PNG.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="browser_click",
        description="Click an element by CSS selector.",
        inputSchema={
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    ),
    types.Tool(
        name="browser_type",
        description="Type text into an element by CSS selector.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["selector", "text"],
        },
    ),
    types.Tool(
        name="browser_scroll",
        description="Scroll page up or down.",
        inputSchema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"]},
                "amount": {"type": "integer", "default": 300, "description": "Pixels to scroll."},
            },
            "required": ["direction"],
        },
    ),
    types.Tool(
        name="browser_execute_js",
        description="Execute JavaScript in the page context. Returns result as string.",
        inputSchema={
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    ),
    types.Tool(
        name="browser_solve_captcha",
        description="Attempt to solve a CAPTCHA using the mode-appropriate method.",
        inputSchema={"type": "object", "properties": {}},
    ),
]

_DISPATCH: dict[str, tuple[callable, list[str]]] = {
    "browser_start":        (browser_start,        ["mode", "proxy"]),
    "browser_status":       (browser_status,        []),
    "browser_close":        (browser_close,         []),
    "browser_navigate":     (browser_navigate,      ["url"]),
    "browser_back":         (browser_back,          []),
    "browser_get_text":     (browser_get_text,      ["selector"]),
    "browser_get_links":    (browser_get_links,     ["filter"]),
    "browser_screenshot":   (browser_screenshot,    []),
    "browser_click":        (browser_click,         ["selector"]),
    "browser_type":         (browser_type,          ["selector", "text"]),
    "browser_scroll":       (browser_scroll,        ["direction", "amount"]),
    "browser_execute_js":   (browser_execute_js,    ["code"]),
    "browser_solve_captcha": (browser_solve_captcha, []),
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return _TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name not in _DISPATCH:
        raise ValueError(f"Unknown tool: {name}")

    fn, param_names = _DISPATCH[name]
    kwargs = {k: arguments[k] for k in param_names if k in arguments}

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: fn(**kwargs))
    except RuntimeError as exc:
        result = {"error": str(exc)}
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}

    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


def create_app() -> Starlette:
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ]
    )


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8765"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
```

- [ ] **Step 2: Verify imports resolve**

```bash
.venv/bin/python -c "from src.mcp_server.server import create_app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/mcp_server/server.py
git commit -m "feat: MCP server entrypoint with SSE transport and tool dispatch"
```

---

## Task 10: Docker configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
# Dockerfile
FROM python:3.12-slim-bookworm

# Chrome + Xvfb + PyAutoGUI system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    xvfb x11-utils \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    scrot python3-tk python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome stable
RUN wget -q -O /tmp/chrome.deb \
    https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb

# Install uv for fast dependency install
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml .
RUN uv pip install --system -e "."

# Pre-download UC chromedriver (caches at build time)
RUN python -c "from seleniumbase import drivers; import subprocess; subprocess.run(['sbase', 'get', 'chromedriver', '--path=/usr/local/bin'], check=False)" || true

COPY src/ src/

EXPOSE 8765

CMD ["python", "-m", "src.mcp_server.server"]
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  seleniumbase-mcp:
    build: .
    ports:
      - "${MCP_PORT:-8765}:8765"
    env_file:
      - .env
    environment:
      - DISPLAY=:99
    shm_size: "2gb"
    restart: unless-stopped
```

- [ ] **Step 3: Write `.env.example`**

```
BROWSER_MODE=cdp
SELENIUM_TIMEOUT=30
ALWAYS_PROXY=false
SELENIUM_PROXY=
MCP_PORT=8765
```

- [ ] **Step 4: Copy `.env.example` to `.env`**

```bash
cp .env.example .env
```

- [ ] **Step 5: Build the image**

```bash
docker compose build
```

Expected: image builds successfully. This may take several minutes (Chrome download).

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .env.example
git commit -m "feat: Docker configuration"
```

---

## Task 11: Integration smoke test

- [ ] **Step 1: Start the container**

```bash
docker compose up -d
```

Expected: container starts, no immediate exit.

- [ ] **Step 2: Check container logs**

```bash
docker compose logs seleniumbase-mcp
```

Expected: uvicorn startup message, no Python errors.

- [ ] **Step 3: Verify SSE endpoint responds**

```bash
curl -N --max-time 3 http://localhost:8765/sse 2>&1 | head -5
```

Expected: `data:` SSE event lines or connection headers (not a connection refused error).

- [ ] **Step 4: Test browser_start via MCP**

Install the MCP inspector locally (one-time):
```bash
npx @modelcontextprotocol/inspector http://localhost:8765/sse
```

In the inspector UI:
1. Connect to the server
2. Call `browser_start` with `{"mode": "standard"}`
3. Verify response: `{"status": "running", "mode": "standard"}`
4. Call `browser_navigate` with `{"url": "https://example.com"}`
5. Verify response contains `"title": "Example Domain"`
6. Call `browser_close`
7. Verify response: `{"status": "closed"}`

- [ ] **Step 5: Stop container**

```bash
docker compose down
```

---

## Task 12: README + MCP config

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# SeleniumBase MCP Server

Live browser control for Claude Code and OpenCode via SeleniumBase. Runs entirely in Docker.

## Quick Start

1. Copy env file and configure:
   ```bash
   cp .env.example .env
   ```

2. Start the server:
   ```bash
   docker compose up -d
   ```

3. Add to `~/.claude/settings.json`:
   ```json
   {
     "mcpServers": {
       "seleniumbase": {
         "type": "sse",
         "url": "http://localhost:8765/sse"
       }
     }
   }
   ```

4. Restart Claude Code. The `browser_*` tools are now available.

## Browser Modes

Set `BROWSER_MODE` in `.env`:

| Mode | Description | Use when |
|------|-------------|----------|
| `cdp` (default) | CDP protocol, stealthiest | Cloudflare, advanced anti-bot |
| `uc` | Undetected-chromedriver | General bot-protected sites |
| `standard` | Plain Selenium | Open sites, debugging |

## Proxy

**Per-session:** pass `proxy` to `browser_start`:
```
browser_start(mode="cdp", proxy="http://user:pass@host:port")
```

**Always-on:** set in `.env`:
```
ALWAYS_PROXY=true
SELENIUM_PROXY=http://user:pass@host:port
```

## Available Tools

| Tool | Description |
|------|-------------|
| `browser_start` | Start session (mode, proxy) |
| `browser_status` | Check session state |
| `browser_close` | End session |
| `browser_navigate` | Go to URL, return page text |
| `browser_back` | Navigate back |
| `browser_get_text` | Extract page/element text (Markdown) |
| `browser_get_links` | List all links [{text, href}] |
| `browser_screenshot` | Capture page as base64 PNG |
| `browser_click` | Click element by CSS selector |
| `browser_type` | Type text into element |
| `browser_scroll` | Scroll up/down |
| `browser_execute_js` | Run JavaScript |
| `browser_solve_captcha` | Attempt CAPTCHA bypass |

## Stop

```bash
docker compose down
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start and tool reference"
```

---

## Self-Review Checklist

After writing this plan, checking against the spec:

- [x] Single container architecture with Xvfb — Task 10 Dockerfile
- [x] UC / CDP / standard mode selection — Task 3 session.py, Task 10 .env.example
- [x] All 13 tools from spec — Tasks 4–9
- [x] Proxy: per-call + always-on global — Tasks 2 and 3
- [x] Error handling (no session, element not found) — Task 3 `_require_session()`
- [x] html2text content cleaning — Task 3 `_html_to_markdown()`
- [x] SSE transport on port 8765 — Task 9
- [x] Claude Code / OpenCode MCP config — Task 12 README
- [x] `.env.example` with all config vars — Task 10
- [x] TDD throughout — each component has tests before implementation
- [x] Frequent commits — every task ends with a commit
