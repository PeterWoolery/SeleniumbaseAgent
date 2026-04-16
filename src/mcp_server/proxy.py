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
