#!/usr/bin/env python3
"""Run the 120-case tool-selection benchmark through a real local MCP host.

The adapter starts the checked-out Arbitype STDIO server, obtains its advertised
tool catalog through ``tools/list``, and asks TypeSafe Jev to select one tool
for each public case.  It intentionally does not execute the selected tool:
the dataset evaluates selection, while the schema check validates a small,
deterministic fixture call against the server's advertised input schema.

This is an opt-in live benchmark.  It requires ``TYPESAFE_API_KEY`` and is not
used by normal CI.  Reports contain case ids and aggregate results, never the
credential or raw provider prompts/responses.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arbitype.core import BridgeError, Settings, TypeSafeClient  # noqa: E402
from arbitype.mcp import TOOL_MAP, _matches_json_schema  # noqa: E402
from scripts.run_tool_selection_eval import load_cases, score_cases  # noqa: E402


DECISION_TOOLS = tuple(
    name for name in TOOL_MAP if name != "health"
)


def default_output_path() -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ROOT / "evals" / "reports" / f"tool-selection-{today}.json"


class HostProtocolError(RuntimeError):
    """Raised when the local MCP host does not return a valid JSON-RPC result."""


class StdioHost:
    """Minimal MCP host adapter used only for this offline/local catalog step."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.request_id = 0

    def __enter__(self) -> "StdioHost":
        self.process = subprocess.Popen(
            [sys.executable, "-m", "arbitype"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            initialized = self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "arbitype-tool-selection-eval", "version": "0.7.0-dev"},
                },
            )
            protocol = initialized.get("protocolVersion")
            if not isinstance(protocol, str):
                raise HostProtocolError("MCP initialize response has no protocolVersion")
            self.request_notification("notifications/initialized", {})
            tools_result = self.request("tools/list", {})
            tools = tools_result.get("tools")
            if not isinstance(tools, list):
                raise HostProtocolError("MCP tools/list response has no tools array")
            self.tools = {
                item["name"]: item
                for item in tools
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            self.protocol_version = protocol
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.request_id += 1
        request = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params}
        self._write(request)
        raw = self._readline()
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HostProtocolError(f"invalid JSON-RPC response for {method}") from exc
        if not isinstance(response, dict) or response.get("id") != self.request_id:
            raise HostProtocolError(f"unexpected JSON-RPC response for {method}")
        if "error" in response:
            raise HostProtocolError(f"MCP {method} returned an error")
        result = response.get("result")
        if not isinstance(result, dict):
            raise HostProtocolError(f"MCP {method} returned no result object")
        return result

    def request_notification(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _write(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise HostProtocolError("MCP host is not running")
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _readline(self) -> str:
        if self.process is None or self.process.stdout is None:
            raise HostProtocolError("MCP host is not running")
        line = self.process.stdout.readline()
        if not line:
            raise HostProtocolError("MCP host closed stdout unexpectedly")
        return line

    def close(self) -> None:
        process = self.process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    self.request("shutdown", {})
                except (OSError, HostProtocolError):
                    pass
                try:
                    self.request_notification("exit", {})
                except (OSError, HostProtocolError):
                    pass
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait(timeout=5)
        finally:
            self.process = None


def fixture_arguments(tool: str, prompt: str) -> dict[str, Any]:
    """Build a non-networking, schema-checkable call fixture for one case."""

    if tool == "evaluate":
        return {
            "state": prompt,
            "questions": {
                "decision": {"type": "noul", "instructions": prompt},
            },
        }
    if tool == "classify":
        return {
            "state": prompt,
            "instructions": prompt,
            "labels": {"first": "First category", "second": "Second category"},
        }
    if tool == "score":
        return {"state": prompt, "instructions": prompt, "levels": ["low", "high"]}
    if tool == "check":
        return {"state": prompt, "instructions": prompt}
    if tool == "verify":
        return {"state": prompt, "claims": {"claim": prompt}}
    if tool in {"gate", "review"}:
        return {"state": prompt, "checks": {"check": prompt}}
    if tool == "route":
        return {
            "state": prompt,
            "instructions": prompt,
            "actions": {"continue": "Continue", "stop": "Stop"},
        }
    if tool == "health":
        return {"live": False}
    return {}


def _model_choice(client: TypeSafeClient, prompt: str, catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    criteria = {
        name: item.get("description", "")
        for name, item in catalog.items()
        if name in TOOL_MAP
    }
    response = client.evaluate(
        {
            "state": {"task": prompt, "available_tools": criteria},
            "questions": {
                "tool": {
                    "type": "choice",
                    "instructions": (
                        "Select the one Arbitype MCP tool that best matches the task. "
                        "Return the tool choice only; do not execute it."
                    ),
                    "criteria": criteria,
                }
            },
        }
    )
    answers = response.get("answers")
    answer = answers.get("tool") if isinstance(answers, dict) else None
    if not isinstance(answer, dict):
        raise BridgeError("model response did not contain a tool choice")
    return {"answer": answer, "model": response.get("model"), "usage": response.get("usage")}


def _prediction(
    case: dict[str, Any],
    model_result: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    answer = model_result["answer"]
    selected = answer.get("choice")
    schema_valid = False
    if isinstance(selected, str) and selected in catalog and selected in TOOL_MAP:
        arguments = fixture_arguments(selected, case["prompt"])
        schema = catalog[selected].get("inputSchema")
        schema_valid = isinstance(schema, dict) and _matches_json_schema(arguments, schema)
    return {
        "id": case["id"],
        "selected_tool": selected if isinstance(selected, str) else None,
        "schema_valid": schema_valid,
    }


def run(cases: list[dict[str, Any]], output_path: Path) -> dict[str, Any]:
    if not os.getenv("TYPESAFE_API_KEY", "").strip():
        raise RuntimeError("tool-selection live benchmark requires TYPESAFE_API_KEY in the process environment")
    settings = Settings.from_env()
    client = TypeSafeClient(settings)
    predictions: list[dict[str, Any]] = []
    model_names: set[str] = set()
    errors = 0
    started = time.monotonic()
    with StdioHost() as host:
        catalog = {name: host.tools[name] for name in DECISION_TOOLS if name in host.tools}
        missing = sorted(set(DECISION_TOOLS) - set(catalog))
        if missing:
            raise HostProtocolError(f"MCP host did not advertise required tools: {', '.join(missing)}")
        for index, case in enumerate(cases, 1):
            try:
                result = _model_choice(client, case["prompt"], catalog)
                if isinstance(result.get("model"), str):
                    model_names.add(result["model"])
                predictions.append(_prediction(case, result, catalog))
            except Exception as exc:  # keep the complete case set visible in the report
                errors += 1
                predictions.append({"id": case["id"], "selected_tool": None, "schema_valid": False})
                print(f"case {index}/{len(cases)} ({case['id']}) failed: {type(exc).__name__}", file=sys.stderr)

    score = score_cases(cases, predictions)
    dataset_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report = {
        "benchmark": "arbitype-tool-selection",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dataset": {
            "path": "evals/tool_selection/cases.jsonl",
            "cases": len(cases),
            "commit": dataset_commit,
        },
        "host": {
            "name": "Arbitype local STDIO MCP host",
            "command": [sys.executable, "-m", "arbitype"],
            "protocol_version": host.protocol_version,
            "advertised_tool_count": len(host.tools),
        },
        "model": {
            "provider": "TypeSafe Jev",
            "requested": settings.model,
            "resolved": sorted(model_names),
            "temperature": None,
            "settings_note": "This adapter does not expose a temperature setting.",
        },
        "runtime": {
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "provider_errors": errors,
            "api_key_recorded": False,
        },
        "scoring_note": (
            "schema_valid_call_rate validates deterministic fixture arguments against "
            "the actual tools/list input schema; the public dataset contains no model-generated arguments."
        ),
        "score": score,
        "predictions": predictions,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/tool_selection/cases.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    output_path = args.output or default_output_path()
    try:
        cases = load_cases(args.dataset)
        report = run(cases, output_path)
    except (OSError, RuntimeError, BridgeError, HostProtocolError, subprocess.CalledProcessError) as exc:
        print(f"tool-selection-live: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["score"], ensure_ascii=False, indent=2, sort_keys=True))
    print(f"report: {output_path}")
    return 0 if report["runtime"]["provider_errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
