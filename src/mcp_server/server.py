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

_DISPATCH: dict[str, tuple] = {
    "browser_start":         (browser_start,         ["mode", "proxy"]),
    "browser_status":        (browser_status,         []),
    "browser_close":         (browser_close,          []),
    "browser_navigate":      (browser_navigate,       ["url"]),
    "browser_back":          (browser_back,           []),
    "browser_get_text":      (browser_get_text,       ["selector"]),
    "browser_get_links":     (browser_get_links,      ["filter"]),
    "browser_screenshot":    (browser_screenshot,     []),
    "browser_click":         (browser_click,          ["selector"]),
    "browser_type":          (browser_type,           ["selector", "text"]),
    "browser_scroll":        (browser_scroll,         ["direction", "amount"]),
    "browser_execute_js":    (browser_execute_js,     ["code"]),
    "browser_solve_captcha": (browser_solve_captcha,  []),
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
