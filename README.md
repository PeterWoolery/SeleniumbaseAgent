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

## Development

Run tests locally:
```bash
uv venv .venv
uv pip install -e ".[dev]"
.venv/bin/pytest
```
