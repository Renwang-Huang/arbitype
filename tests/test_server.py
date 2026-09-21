import io
import json
import os
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typesafe_codex_mcp import core, mcp  # noqa: E402


def noul_response(question_id="ready", value=0.9):
    return {
        "model": "jev-1.13.0",
        "answers": {question_id: {"type": "noul", "noul": value}},
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }


def choice_response(question_id="classification", choice="billing"):
    return {
        "model": "jev-1.13.0",
        "answers": {
            question_id: {
                "type": "choice",
                "choice": choice,
                "probabilities": {"billing": 0.9, "technical": 0.1},
                "confidence": 0.82,
            }
        },
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }


class FakeResponse:
    def __init__(self, payload, headers=None, status=200):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        if limit >= 0:
            return self.payload[:limit]
        return self.payload


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.settings = core.Settings(api_key="secret", retry_jitter=0, max_request_bytes=10_000)

    def test_valid_payload_defaults_model(self):
        payload = core.validate_request(
            {
                "state": {"message": "hello"},
                "questions": {
                    "urgent": {"type": "noul", "instructions": "Is this urgent?"},
                    "team": {
                        "type": "choice",
                        "instructions": "Which team?",
                        "criteria": {"support": None, "engineering": None},
                    },
                    "severity": {
                        "type": "score",
                        "instructions": "How severe?",
                        "criteria": ["low", "high"],
                    },
                },
            },
            self.settings,
        )
        self.assertEqual(payload["model"], "jev-latest")

    def test_rejects_unknown_fields_and_invalid_shapes(self):
        with self.assertRaisesRegex(core.BridgeError, "unsupported argument"):
            core.validate_request(
                {
                    "state": "hello",
                    "questions": {"q": {"type": "noul", "instructions": "?"}},
                    "debug": True,
                },
                self.settings,
            )
        with self.assertRaises(core.BridgeError):
            core.validate_request(
                {"state": True, "questions": {"q": {"type": "noul", "instructions": "?"}}},
                self.settings,
            )

    def test_choice_and_score_limits_are_enforced(self):
        labels = {str(index): None for index in range(256)}
        with self.assertRaisesRegex(core.BridgeError, "255"):
            core.validate_request(
                {
                    "state": "hello",
                    "questions": {"q": {"type": "choice", "instructions": "?", "criteria": labels}},
                },
                self.settings,
            )
        with self.assertRaises(core.BridgeError):
            core.validate_request(
                {
                    "state": "hello",
                    "questions": {
                        "q": {
                            "type": "score",
                            "instructions": "?",
                            "criteria": list(range(11)),
                        }
                    },
                },
                self.settings,
            )

    def test_payload_size_is_checked_before_network(self):
        small = core.Settings(api_key="secret", max_state_chars=10, max_request_bytes=100)
        with self.assertRaisesRegex(core.BridgeError, "state exceeds"):
            core.validate_request(
                {"state": "this is too long", "questions": {"q": {"type": "noul", "instructions": "?"}}},
                small,
            )


class ResponseTests(unittest.TestCase):
    def test_validates_choice_distribution_and_argmax(self):
        questions = {
            "classification": {
                "type": "choice",
                "instructions": "Which?",
                "criteria": {"billing": None, "technical": None},
            }
        }
        response = core.validate_api_response(choice_response(), questions)
        self.assertEqual(response["answers"]["classification"]["choice"], "billing")

        bad = choice_response()
        bad["answers"]["classification"]["choice"] = "technical"
        with self.assertRaisesRegex(core.APIError, "top probability"):
            core.validate_api_response(bad, questions)

    def test_rejects_missing_or_malformed_answers(self):
        with self.assertRaisesRegex(core.APIError, "missing answer"):
            core.validate_api_response(noul_response(), {"other": {"type": "noul"}})
        malformed = noul_response()
        malformed["answers"]["ready"]["noul"] = 2
        with self.assertRaisesRegex(core.APIError, "invalid noul"):
            core.validate_api_response(malformed, {"ready": {"type": "noul"}})


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.settings = core.Settings(
            api_key="secret-key",
            max_retries=2,
            retry_backoff_seconds=1,
            max_backoff_seconds=10,
            retry_jitter=0,
        )
        self.payload = {
            "state": "hello",
            "questions": {"ready": {"type": "noul", "instructions": "Is this ready?"}},
        }

    def test_retries_429_respecting_retry_after(self):
        error = HTTPError(
            "https://api.typesafe.ai/v1/systemone",
            429,
            "rate limited",
            {"Retry-After": "0", "x-typesafe-request-id": "req-1"},
            io.BytesIO(b'{"message":"api_key=secret-key"}'),
        )
        sleeps = []
        with patch.object(core, "urlopen", side_effect=[error, FakeResponse(noul_response())]) as opener:
            response = core.post_to_typesafe(self.payload, settings=self.settings, sleep=sleeps.append)
        self.assertEqual(response["answers"]["ready"]["noul"], 0.9)
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(sleeps, [0.0])

    def test_retries_support_typesafe_millisecond_hint(self):
        error = HTTPError(
            "https://api.typesafe.ai/v1/systemone",
            529,
            "overloaded",
            {"retry-after-ms": "1250"},
            io.BytesIO(b"overloaded"),
        )
        sleeps = []
        with patch.object(core, "urlopen", side_effect=[error, FakeResponse(noul_response())]):
            core.post_to_typesafe(self.payload, settings=self.settings, sleep=sleeps.append)
        self.assertEqual(sleeps, [1.25])

    def test_non_retryable_error_is_bounded_and_redacted(self):
        error = HTTPError(
            "https://api.typesafe.ai/v1/systemone",
            401,
            "unauthorized",
            {},
            io.BytesIO(b'{"message":"Authorization: Bearer secret-key"}'),
        )
        with patch.object(core, "urlopen", side_effect=error):
            with self.assertRaises(core.APIError) as raised:
                core.post_to_typesafe(self.payload, settings=self.settings)
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertIn("redacted", str(raised.exception))

    def test_api_key_is_sent_only_as_authorization_header(self):
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse(noul_response())

        with patch.object(core, "urlopen", side_effect=opener):
            core.post_to_typesafe(self.payload, settings=self.settings)
        self.assertEqual(captured["request"].get_header("Authorization"), "Bearer secret-key")
        self.assertNotIn("secret-key", captured["request"].data.decode())


class ProtocolTests(unittest.TestCase):
    def test_initialize_and_tool_list(self):
        response = mcp.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
        )
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertIn("tools", response["result"]["capabilities"])
        listed = mcp.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertEqual(
            {tool["name"] for tool in listed["result"]["tools"]},
            {"evaluate", "classify", "score", "check", "verify", "gate"},
        )

    def test_notifications_and_invalid_protocol(self):
        self.assertIsNone(mcp.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(mcp.handle_message({"id": 1, "method": "ping"})["error"]["code"], -32600)

    def test_classify_tool_uses_one_typed_question(self):
        class FakeClient:
            settings = core.Settings(api_key="secret")

            def evaluate(self, request):
                self.request = request
                return choice_response()

        with patch.object(mcp, "TypeSafeClient", return_value=FakeClient()):
            response = mcp.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "classify",
                        "arguments": {
                            "state": "payment failed",
                            "instructions": "Which team?",
                            "labels": {"billing": None, "technical": None},
                        },
                    },
                }
            )
        self.assertEqual(response["result"]["structuredContent"]["answer"]["choice"], "billing")

    def test_gate_is_deterministic_and_fail_closed(self):
        class FakeClient:
            settings = core.Settings(api_key="secret")

            def evaluate(self, request):
                return {
                    "model": "jev-1.13.0",
                    "answers": {
                        "safe": {"type": "noul", "noul": 0.55},
                        "complete": {"type": "noul", "noul": 0.95},
                    },
                }

        with patch.object(mcp, "TypeSafeClient", return_value=FakeClient()):
            result = mcp.call_tool(
                "gate",
                {"state": "patch", "checks": {"safe": "safe?", "complete": "complete?"}},
            )
        self.assertEqual(result["decision"], "fail")
        self.assertEqual(result["checks"]["safe"]["decision"], "fail")


class CLITests(unittest.TestCase):
    def test_doctor_json_does_not_print_secret(self):
        from typesafe_codex_mcp.cli import main

        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret-key"}, clear=True), patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(main(["doctor", "--json"]), 0)
        output = stdout.getvalue()
        self.assertIn('"api_key_configured": true', output)
        self.assertNotIn("secret-key", output)


if __name__ == "__main__":
    unittest.main()
