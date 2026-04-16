# SeleniumBase MCP Server — Design Spec

**Date:** 2026-04-15  
**Status:** Approved for implementation

---

## Overview

An MCP server that gives Claude Code and OpenCode live browser control via SeleniumBase, running entirely in Docker. Designed for ad-hoc web recon and reconnaissance — not bulk scraping (agents write scripts for that). Supports UC mode and CDP mode for bot-detection evasion, with optional proxy routing.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Host Machine                      │
│                                                     │
│  Claude Code / OpenCode                             │
│       │  HTTP/SSE :8765                             │
│       ▼                                             │
│  ┌─────────────────────────────────────────────┐   │
│  │          seleniumbase-mcp container          │   │
│  │                                             │   │
│  │  Xvfb (virtual display)                     │   │
│  │  Chrome (UC-patched chromedriver)            │   │
│  │  SeleniumBase (SB manager, uc=True)          │   │
│  │  PyAutoGUI (CAPTCHA handling on Linux)       │   │
│  │  MCP server → exposes SSE on :8765           │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Single container** — UC mode uses `undetected-chromedriver`, which patches Chrome binaries directly and cannot operate over a remote WebDriver connection. Chrome, SeleniumBase, and the MCP server must share the same process space.

**Transport:** HTTP/SSE on `localhost:8765`. Allows Claude Code and OpenCode to connect to the same endpoint without per-client reconfiguration. No local Python install required — `docker-compose up` is the only start command.

---

## Browser Modes

All modes initialize with `SB(uc=True)`. Mode affects only the navigation method.

| Mode | Nav method | Stealth level | Use when |
|------|-----------|---------------|----------|
| `cdp` *(default)* | `sb.activate_cdp_mode(url)` | Highest — pure CDP, no WebDriver fingerprint | Cloudflare, advanced anti-bot |
| `uc` | `sb.uc_open_with_reconnect(url)` | High — WebDriver disconnect/reconnect | General bot-protected sites |
| `standard` | `sb.open(url)` | None | Open sites, debugging |

Mode is selected at session start and held for the session lifetime.

---

## Session Model

**Stateful, single session.** The MCP server maintains one live SeleniumBase browser session. State (cookies, auth, page context) persists across tool calls until `browser_close` or container restart.

Session lifecycle:
1. `browser_start` → spawns `SB(uc=True)`, sets mode and proxy, returns ready status
2. Tool calls operate on the running session
3. `browser_close` → quits browser, clears session state
4. If the session crashes → `browser_status` returns `disconnected`; call `browser_start` to recover

No persistent session storage — sessions are ephemeral by design.

---

## Tool API

### Session lifecycle

| Tool | Params | Returns |
|------|--------|---------|
| `browser_start` | `mode?: cdp\|uc\|standard`, `proxy?: str` | session status, browser info |
| `browser_status` | — | `running\|stopped\|disconnected`, current URL |
| `browser_close` | — | confirmation |

### Navigation

| Tool | Params | Returns |
|------|--------|---------|
| `browser_navigate` | `url: str` | page title, cleaned Markdown text, final URL |
| `browser_back` | — | new URL, page text |

### Extraction

| Tool | Params | Returns |
|------|--------|---------|
| `browser_get_text` | `selector?: str` | Markdown-cleaned text of element or full page |
| `browser_get_links` | `filter?: str` | list of `{text, href}`, filterable by domain/pattern |
| `browser_screenshot` | — | base64-encoded PNG |

### Interaction

| Tool | Params | Returns |
|------|--------|---------|
| `browser_click` | `selector: str` | new URL or confirmation |
| `browser_type` | `selector: str, text: str` | confirmation |
| `browser_scroll` | `direction: up\|down, amount?: int` | confirmation |
| `browser_execute_js` | `code: str` | JS return value as string |

### CAPTCHA

| Tool | Params | Returns |
|------|--------|---------|
| `browser_solve_captcha` | — | success/failure; calls `sb.solve_captcha()` (CDP), `sb.uc_gui_click_captcha()` (UC), no-op (standard) |

**Content cleaning:** `browser_get_text` strips scripts/styles via `html2text`, returning readable Markdown. Raw HTML never reaches Claude.

---

## Proxy Configuration

Two layers, applied in priority order:

1. **Per-call** — `proxy` param on `browser_start` overrides everything for that session
2. **Global** — `SELENIUM_PROXY` + `ALWAYS_PROXY=true` in `.env` applies to every session automatically

When `ALWAYS_PROXY=false` (default), no proxy is used unless passed to `browser_start`.

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Element not found | Descriptive error returned; session stays alive |
| Navigation timeout | Error returned after `SELENIUM_TIMEOUT` seconds; session stays alive |
| Container unreachable | Tool returns connection error; MCP server stays up |
| Unhandled JS exception | Caught, returned as error string |
| Session crash | `browser_status` returns `disconnected`; user calls `browser_start` to recover |

---

## Configuration

**`.env.example`** (committed; actual `.env` gitignored):

```
BROWSER_MODE=cdp          # cdp | uc | standard
SELENIUM_TIMEOUT=30       # seconds per action
ALWAYS_PROXY=false        # true = force proxy on every session
SELENIUM_PROXY=           # http://user:pass@host:port
MCP_PORT=8765             # SSE port exposed to host
```

---

## Project Structure

```
SeleniumBaseAgent/
├── docker-compose.yml
├── Dockerfile                  # built on official SeleniumBase Docker image
├── .env.example
├── .env                        # gitignored
├── pyproject.toml
├── README.md
└── src/
    └── mcp_server/
        ├── __init__.py
        ├── server.py           # MCP server entrypoint, SSE transport
        ├── session.py          # SB session lifecycle, mode dispatch
        ├── proxy.py            # proxy config resolution (env + per-call)
        └── tools/
            ├── __init__.py
            ├── lifecycle.py    # browser_start, browser_close, browser_status
            ├── navigation.py   # browser_navigate, browser_back
            ├── extraction.py   # browser_get_text, browser_get_links, browser_screenshot
            ├── interaction.py  # browser_click, browser_type, browser_scroll, browser_execute_js
            └── captcha.py      # browser_solve_captcha
```

---

## Claude Code / OpenCode Integration

Add to `~/.claude/settings.json` (or project `.mcp.json`):

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

Start the server: `docker-compose up -d`  
Stop: `docker-compose down`

---

## Out of Scope

- Multiple simultaneous browser sessions
- Session persistence across container restarts
- Script generation / bulk scraping (agents handle that separately)
- Non-Chrome browsers
