#!/usr/bin/env python3
"""Backward-compatible launcher for the TypeSafe MCP bridge.

Keep this file because existing MCP configurations point at it. New
installations can use ``typesafe-mcp`` or ``python -m typesafe_mcp``.
"""

from typesafe_mcp.cli import main
from typesafe_mcp.core import (
    APIError,
    BridgeError,
    ConfigError,
    Settings,
    TypeSafeClient,
    post_to_typesafe as _post_to_typesafe,
    validate_request as _validate_request,
)
from typesafe_mcp.mcp import TOOLS, call_tool, handle_message, main_stdio

__all__ = [
    "APIError",
    "BridgeError",
    "ConfigError",
    "Settings",
    "TypeSafeClient",
    "TOOLS",
    "call_tool",
    "handle_message",
    "main_stdio",
    "_post_to_typesafe",
    "_validate_request",
]


if __name__ == "__main__":
    raise SystemExit(main())
