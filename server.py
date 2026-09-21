#!/usr/bin/env python3
"""Backward-compatible launcher for the Arbitype MCP service.

Keep this file because existing MCP configurations point at it. New
installations can use ``arbitype`` or ``python -m arbitype``.
"""

from arbitype.cli import main
from arbitype.core import (
    APIError,
    BridgeError,
    ConfigError,
    Settings,
    TypeSafeClient,
    post_to_typesafe as _post_to_typesafe,
    validate_request as _validate_request,
)
from arbitype.mcp import TOOLS, call_tool, handle_message, main_stdio

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
