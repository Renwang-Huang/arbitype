#!/usr/bin/env python3
"""Exercise the local server with the official MCP Python SDK client."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]


async def run() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        cwd=str(ROOT),
    )
    async with Client(parameters, read_timeout_seconds=10) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        expected = {
            "evaluate",
            "classify",
            "score",
            "check",
            "verify",
            "gate",
            "route",
            "review",
            "health",
        }
        missing = expected - names
        if missing:
            raise RuntimeError(f"official SDK did not see expected tools: {sorted(missing)}")

        health = await client.call_tool("health", {})
        if health.is_error:
            raise RuntimeError("health tool returned an MCP error")
        if not isinstance(health.structured_content, dict):
            raise RuntimeError("health tool did not return structured content")
        if health.structured_content.get("server") != "arbitype":
            raise RuntimeError("unexpected server identity")

        print(
            json.dumps(
                {
                    "ok": True,
                    "protocol_version": client.protocol_version,
                    "tool_count": len(tools.tools),
                    "server": client.server_info.name if client.server_info else None,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    asyncio.run(run())
