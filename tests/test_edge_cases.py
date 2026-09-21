import io
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError, URLError


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from arbitype import cli, core, mcp  # noqa: E402


class RawResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.payload if limit < 0 else self.payload[:limit]


def noul_payload(question_id="ready", value=0.9):
    return {
        "model": "jev-1.13.0",
        "answers": {question_id: {"type": "noul", "noul": value}},
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }


class SettingsEdgeTests(unittest.TestCase):
    def test_environment_compatibility_and_limits(self):
        values = {
            "TYPESAFE_API_KEY": "secret",
            "TYPESAFE_BASE_URL": "https://example.test/base",
            "TYPESAFE_MODEL": "legacy-model",
            "TYPESAFE_DEFAULT_MODEL": "official-model",
            "TYPESAFE_TIMEOUT_SECONDS": "12.5",
            "TYPESAFE_MAX_RETRIES": "4",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = core.Settings.from_env()
        self.assertEqual(settings.base_url, "https://example.test/base")
        self.assertEqual(settings.model, "legacy-model")
        self.assertEqual(settings.timeout_seconds, 12.5)
        self.assertEqual(settings.max_retries, 4)

    def test_environment_rejects_credentials_query_and_invalid_numbers(self):
        for base_url in (
            "https://user:pass@example.test",
            "https://example.test?a=1",
            "http://example.test",
        ):
            with self.subTest(base_url=base_url), patch.dict(
                os.environ, {"TYPESAFE_BASE_URL": base_url}, clear=True
            ):
                with self.assertRaises(core.ConfigError):
                    core.Settings.from_env(require_key=False)
        with patch.dict(os.environ, {"TYPESAFE_MAX_RETRIES": "not-a-number"}, clear=True):
            with self.assertRaisesRegex(core.ConfigError, "TYPESAFE_MAX_RETRIES"):
                core.Settings.from_env(require_key=False)

    def test_environment_allows_http_only_for_loopback(self):
        for base_url in ("http://127.0.0.1:8080", "http://localhost:8080", "http://[::1]:8080"):
            with self.subTest(base_url=base_url), patch.dict(
                os.environ, {"TYPESAFE_BASE_URL": base_url}, clear=True
            ):
                self.assertEqual(core.Settings.from_env(require_key=False).base_url, base_url)

        with self.assertRaises(core.ConfigError):
            core.Settings(api_key="secret", base_url="http://example.test")

    def test_utf8_byte_limits_are_enforced(self):
        settings = core.Settings(api_key="secret", max_state_chars=4)
        with self.assertRaisesRegex(core.BridgeError, "state exceeds"):
            core.validate_request(
                {"state": "ééé", "questions": {"q": {"type": "noul", "instructions": "?"}}},
                settings,
            )


class ResponseAndTransportEdgeTests(unittest.TestCase):
    def setUp(self):
        self.settings = core.Settings(
            api_key="secret-key",
            max_retries=2,
            retry_backoff_seconds=0,
            retry_jitter=0,
            max_response_bytes=512,
        )
        self.payload = {
            "state": "hello",
            "questions": {"ready": {"type": "noul", "instructions": "Is this ready?"}},
        }

    def test_retry_after_http_date_is_parsed(self):
        future = datetime.now(timezone.utc) + timedelta(seconds=5)
        delay = core._retry_after_from_headers({"Retry-After": format_datetime(future, usegmt=True)})
        self.assertIsNotNone(delay)
        self.assertGreaterEqual(delay, 0)
        self.assertIsNone(core._retry_after_from_headers({"Retry-After": "not-a-date"}))

    def test_network_failures_retry_until_success(self):
        sleeps = []
        with patch.object(
            core,
            "urlopen",
            side_effect=[URLError("down"), URLError("still down"), RawResponse(json.dumps(noul_payload()).encode())],
        ) as opener:
            response = core.post_to_typesafe(self.payload, settings=self.settings, sleep=sleeps.append)
        self.assertEqual(response["answers"]["ready"]["noul"], 0.9)
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(sleeps, [0, 0])

    def test_local_http_server_round_trip_exercises_real_urllib_transport(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                received["path"] = self.path
                received["authorization"] = self.headers.get("Authorization")
                length = int(self.headers.get("Content-Length", "0"))
                received["body"] = json.loads(self.rfile.read(length))
                body = json.dumps(noul_payload()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            settings = core.Settings(
                api_key="secret-key",
                base_url=f"http://127.0.0.1:{server.server_port}/api",
                max_retries=0,
            )
            response = core.post_to_typesafe(self.payload, settings=settings)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(response["answers"]["ready"]["noul"], 0.9)
        self.assertEqual(received["path"], "/api/v1/systemone")
        self.assertEqual(received["authorization"], "Bearer secret-key")
        self.assertEqual(received["body"]["questions"]["ready"]["type"], "noul")

    def test_redirects_never_forward_authorization(self):
        redirect_received = {}
        target_received = {}

        class TargetHandler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                target_received["authorization"] = self.headers.get("Authorization")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(noul_payload()).encode("utf-8"))

            def log_message(self, *_args):
                return

        target_server = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_thread = threading.Thread(target=target_server.serve_forever, daemon=True)
        target_thread.start()

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                redirect_received["authorization"] = self.headers.get("Authorization")
                self.send_response(302)
                self.send_header(
                    "Location",
                    f"http://127.0.0.1:{target_server.server_port}/redirected",
                )
                self.end_headers()

            def log_message(self, *_args):
                return

        redirect_server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        redirect_thread = threading.Thread(target=redirect_server.serve_forever, daemon=True)
        redirect_thread.start()
        try:
            settings = core.Settings(
                api_key="secret-key",
                base_url=f"http://127.0.0.1:{redirect_server.server_port}/api",
                max_retries=0,
            )
            with self.assertRaisesRegex(core.APIError, "HTTP 302"):
                core.post_to_typesafe(self.payload, settings=settings)
        finally:
            redirect_server.shutdown()
            redirect_server.server_close()
            redirect_thread.join(timeout=2)
            target_server.shutdown()
            target_server.server_close()
            target_thread.join(timeout=2)

        self.assertEqual(redirect_received["authorization"], "Bearer secret-key")
        self.assertNotIn("authorization", target_received)

    def test_invalid_json_and_oversized_response_fail_safely(self):
        with patch.object(core, "urlopen", return_value=RawResponse(b"not-json")):
            with self.assertRaisesRegex(core.APIError, "invalid JSON"):
                core.post_to_typesafe(self.payload, settings=self.settings)
        limited = core.Settings(api_key="secret-key", max_retries=0, max_response_bytes=10)
        with patch.object(core, "urlopen", return_value=RawResponse(b"x" * 50)):
            with self.assertRaisesRegex(core.APIError, "exceeded"):
                core.post_to_typesafe(self.payload, settings=limited)

    def test_request_id_is_retained_but_secret_is_redacted(self):
        error = HTTPError(
            "https://api.typesafe.ai/v1/systemone",
            400,
            "bad request",
            {"x-typesafe-request-id": "req-123"},
            io.BytesIO(b'{"message":"Bearer secret-key"}'),
        )
        settings = core.Settings(api_key="secret-key", max_retries=0)
        with patch.object(core, "urlopen", side_effect=error):
            with self.assertRaises(core.APIError) as raised:
                core.post_to_typesafe(self.payload, settings=settings)
        self.assertIn("request_id=req-123", str(raised.exception))
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertIn("redacted", str(raised.exception))

    def test_score_response_schema_is_checked(self):
        questions = {
            "severity": {
                "type": "score",
                "instructions": "How severe?",
                "criteria": ["low", "medium", "high"],
            }
        }
        valid = {
            "model": "jev-1.13.0",
            "answers": {
                "severity": {
                    "type": "score",
                    "score": 1.1,
                    "legend": {"0": "low", "1": "medium", "2": "high"},
                    "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2},
                    "confidence": 0.8,
                }
            },
            "usage": {"input_tokens": 10, "output_tokens": 2},
        }
        self.assertEqual(core.validate_api_response(valid, questions), valid)
        invalid = json.loads(json.dumps(valid))
        invalid["answers"]["severity"]["legend"]["3"] = "extra"
        with self.assertRaises(core.APIError):
            core.validate_api_response(invalid, questions)

    def test_structured_entries_are_accepted(self):
        payload = core.validate_request(
            {
                "state": {"message": "hello", "metadata": None},
                "questions": {
                    "noul": {
                        "type": "noul",
                        "instructions": "Does this look ready?",
                    },
                    "choice": {
                        "type": "choice",
                        "instructions": {"question": "Which?"},
                        "criteria": {"a": None, "b": {"examples": []}},
                    },
                    "score": {
                        "type": "score",
                        "instructions": ["How severe?"],
                        "criteria": [{"level": "low"}, "high"],
                    },
                },
            },
            self.settings,
        )
        self.assertEqual(payload["questions"]["noul"]["instructions"], "Does this look ready?")

    def test_response_requires_official_model_and_usage_fields(self):
        questions = {"ready": {"type": "noul", "instructions": "Ready?"}}
        with self.assertRaisesRegex(core.APIError, "missing a model"):
            core.validate_api_response(
                {"answers": {"ready": {"type": "noul", "noul": 0.9}}, "usage": {}}, questions
            )
        with self.assertRaisesRegex(core.APIError, "missing a usage"):
            core.validate_api_response(
                {"model": "jev-1.13.0", "answers": {"ready": {"type": "noul", "noul": 0.9}}},
                questions,
            )

    def test_score_must_match_probability_weighted_value(self):
        questions = {
            "severity": {
                "type": "score",
                "instructions": "How severe?",
                "criteria": ["low", "medium", "high"],
            }
        }
        response = {
            "model": "jev-1.13.0",
            "answers": {
                "severity": {
                    "type": "score",
                    "score": 0.1,
                    "legend": {"0": "low", "1": "medium", "2": "high"},
                    "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2},
                    "confidence": 0.8,
                }
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        with self.assertRaisesRegex(core.APIError, "disagrees with probabilities"):
            core.validate_api_response(response, questions)


class CLIAndMCPErrorTests(unittest.TestCase):
    def test_doctor_reports_configuration_error_without_secrets(self):
        stdout = io.StringIO()
        with patch.dict(
            os.environ,
            {"TYPESAFE_API_KEY": "secret-key", "TYPESAFE_BASE_URL": "https://user:pass@example.test"},
            clear=True,
        ), patch("sys.stdout", stdout):
            result = cli.main(["doctor", "--json"])
        self.assertEqual(result, 1)
        output = stdout.getvalue()
        self.assertIn('"configuration": "error"', output)
        self.assertNotIn("secret-key", output)
        self.assertNotIn("user:pass", output)

    def test_evaluate_cli_rejects_invalid_json(self):
        stderr = io.StringIO()
        with patch("sys.stdin", io.StringIO("not-json")), patch("sys.stderr", stderr):
            result = cli.main(["evaluate", "--input", "-"])
        self.assertEqual(result, 1)
        self.assertIn("evaluate:", stderr.getvalue())

    def test_provider_configuration_error_is_an_mcp_tool_error(self):
        with patch.dict(os.environ, {}, clear=True):
            response = mcp.handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {"name": "check", "arguments": {"state": "x", "instructions": "ready?"}},
                }
            )
        self.assertTrue(response["result"]["isError"])
        self.assertIn("TYPESAFE_API_KEY", response["result"]["content"][0]["text"])

    def test_health_live_is_explicit_and_uses_one_typed_request(self):
        class FakeClient:
            def __init__(self, settings):
                self.settings = settings
                self.requests = []

            def evaluate(self, request):
                self.requests.append(request)
                return noul_payload()

        fake = FakeClient(core.Settings(api_key="secret"))
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret"}, clear=True), patch.object(
            mcp, "TypeSafeClient", return_value=fake
        ):
            result = mcp.call_tool("health", {"live": True})
        self.assertTrue(result["live"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(fake.requests), 1)


if __name__ == "__main__":
    unittest.main()
