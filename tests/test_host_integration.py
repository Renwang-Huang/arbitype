import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from typesafe_mcp import core, mcp  # noqa: E402


def route_response(choice="inspect"):
    return {
        "model": "jev-1.13.0",
        "answers": {
            "next_action": {
                "type": "choice",
                "choice": choice,
                "probabilities": {"inspect": 0.9, "test": 0.1},
                "confidence": 0.9,
            }
        },
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }


class HostContractTests(unittest.TestCase):
    def test_server_instructions_fit_host_prefix_limit(self):
        self.assertLessEqual(len(mcp.SERVER_INSTRUCTIONS), 512)
        self.assertIn("Host-neutral", mcp.SERVER_INSTRUCTIONS)
        self.assertIn("route", mcp.SERVER_INSTRUCTIONS)
        self.assertIn("review", mcp.SERVER_INSTRUCTIONS)
        self.assertIn("never edit files", mcp.SERVER_INSTRUCTIONS)

    def test_tools_are_read_only_and_have_structured_output_schema(self):
        self.assertEqual(set(mcp.TOOL_MAP), {tool["name"] for tool in mcp.TOOLS})
        for tool in mcp.TOOLS:
            self.assertTrue(tool["annotations"]["readOnlyHint"], tool["name"])
            self.assertFalse(tool["annotations"]["destructiveHint"], tool["name"])
            self.assertTrue(tool["annotations"]["idempotentHint"], tool["name"])
            self.assertEqual(tool["outputSchema"], {"type": "object"})
            self.assertEqual(tool["inputSchema"]["additionalProperties"], False)

    def test_initialize_advertises_tools_only(self):
        response = mcp.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        self.assertEqual(response["result"]["capabilities"], {"tools": {"listChanged": False}})

    def test_health_is_local_and_does_not_require_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = mcp.call_tool("health", {})
        self.assertEqual(result["type"], "health")
        self.assertEqual(result["status"], "missing_api_key")
        self.assertFalse(result["live"])

    def test_health_rejects_implicit_live_requests(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret"}, clear=True):
            with self.assertRaisesRegex(core.BridgeError, "live must be a boolean"):
                mcp.call_tool("health", {"live": "yes"})

    def test_route_creates_a_single_choice_question(self):
        class FakeClient:
            settings = core.Settings(api_key="secret")

            def __init__(self):
                self.request = None

            def evaluate(self, request):
                self.request = request
                return route_response()

        fake = FakeClient()
        with patch.object(mcp, "TypeSafeClient", return_value=fake):
            result = mcp.call_tool(
                "route",
                {
                    "state": "The patch changes authentication and has no test output.",
                    "actions": {"inspect": "Read the diff", "test": "Run focused tests"},
                },
            )
        self.assertEqual(result["type"], "route")
        self.assertEqual(result["route"], "inspect")
        self.assertEqual(fake.request["questions"]["next_action"]["type"], "choice")

    def test_review_is_a_named_gate_with_fail_closed_result(self):
        class FakeClient:
            settings = core.Settings(api_key="secret")

            def evaluate(self, request):
                return {
                    "model": "jev-1.13.0",
                    "answers": {
                        "tests": {"type": "noul", "noul": 0.55},
                        "scope": {"type": "noul", "noul": 0.95},
                    },
                }

        with patch.object(mcp, "TypeSafeClient", return_value=FakeClient()):
            result = mcp.call_tool(
                "review",
                {"state": "diff", "checks": {"tests": "Tests cover the change", "scope": "Scope is bounded"}},
            )
        self.assertEqual(result["type"], "review")
        self.assertEqual(result["decision"], "fail")
        self.assertEqual(result["checks"]["tests"]["decision"], "fail")

    def test_legacy_tool_aliases_are_callable_but_not_advertised(self):
        self.assertEqual(mcp.TOOL_ALIASES, {"codex_route": "route", "codex_review": "review"})
        self.assertNotIn("codex_route", {tool["name"] for tool in mcp.TOOLS})
        self.assertNotIn("codex_review", {tool["name"] for tool in mcp.TOOLS})

        class FakeClient:
            settings = core.Settings(api_key="secret")

            def evaluate(self, _request):
                return route_response()

        with patch.object(mcp, "TypeSafeClient", return_value=FakeClient()):
            result = mcp.call_tool(
                "codex_route",
                {"state": "state", "actions": {"inspect": "Inspect", "test": "Test"}},
            )
        self.assertEqual(result["type"], "route")

    def test_unexpected_tool_errors_are_safe_mcp_results(self):
        class BrokenClient:
            settings = core.Settings(api_key="secret")

            def evaluate(self, _request):
                raise RuntimeError("secret-key leaked from provider")

        with patch.object(mcp, "TypeSafeClient", return_value=BrokenClient()):
            response = mcp.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {
                        "name": "check",
                        "arguments": {"state": "x", "instructions": "Is x ready?"},
                    },
                }
            )
        self.assertTrue(response["result"]["isError"])
        self.assertNotIn("secret-key", json.dumps(response))
        self.assertEqual(response["result"]["content"][0]["text"], "internal tool error")


class StdioIntegrationTests(unittest.TestCase):
    def test_stdio_handshake_tool_catalog_and_shutdown(self):
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
            {"jsonrpc": "2.0", "method": "exit"},
            {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}},
        ]
        child_env = dict(os.environ)
        child_env.pop("TYPESAFE_API_KEY", None)
        completed = subprocess.run(
            [sys.executable, "server.py"],
            cwd=ROOT,
            input="\n".join(json.dumps(message) for message in messages) + "\n",
            text=True,
            capture_output=True,
            env=child_env,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([response["id"] for response in responses], [1, 2, 3])
        self.assertEqual(responses[0]["result"]["serverInfo"]["version"], mcp.SERVER_VERSION)
        self.assertIn("review", {tool["name"] for tool in responses[1]["result"]["tools"]})
        self.assertEqual(responses[2]["result"], {})

    def test_stdio_rejects_malformed_messages_without_tracebacks(self):
        child_env = dict(os.environ)
        child_env.pop("TYPESAFE_API_KEY", None)
        completed = subprocess.run(
            [sys.executable, "server.py"],
            cwd=ROOT,
            input="{not-json\n[]\n{\"jsonrpc\":\"2.0\",\"method\":\"exit\"}\n",
            text=True,
            capture_output=True,
            env=child_env,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([response["error"]["code"] for response in responses], [-32700, -32700])


if __name__ == "__main__":
    unittest.main()
