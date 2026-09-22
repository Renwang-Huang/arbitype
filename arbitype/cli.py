"""Arbitype CLI entry points for MCP, diagnostics, and JSON evaluation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from .core import BridgeError, SERVER_NAME, SERVER_VERSION, Settings, TypeSafeClient
from .mcp import main_stdio


def _json_dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def _doctor(args: argparse.Namespace) -> int:
    checks: dict[str, Any] = {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "api_key_configured": bool(os.getenv("TYPESAFE_API_KEY", "").strip()),
        "live": False,
    }
    try:
        settings = Settings.from_env(require_key=False)
        checks.update({"base_url": settings.base_url, "model": settings.model, "configuration": "ok"})
    except BridgeError as exc:
        checks.update({"configuration": "error", "message": str(exc)})
        if args.json:
            _json_dump(checks)
        else:
            print(f"configuration: error — {exc}", file=sys.stderr)
        return 1

    if args.live:
        if not checks["api_key_configured"]:
            checks.update({"live": False, "message": "TYPESAFE_API_KEY is not set"})
            if args.json:
                _json_dump(checks)
            else:
                print("live: skipped — TYPESAFE_API_KEY is not set", file=sys.stderr)
            return 1
        started = time.monotonic()
        try:
            TypeSafeClient(settings).evaluate(
                {
                    "state": "health check",
                    "questions": {
                        "ready": {"type": "noul", "instructions": "Is this a health check?"}
                    },
                }
            )
        except BridgeError as exc:
            checks.update({"live": False, "message": str(exc)})
            if args.json:
                _json_dump(checks)
            else:
                print(f"live: error — {exc}", file=sys.stderr)
            return 1
        checks.update({"live": True, "latency_ms": round((time.monotonic() - started) * 1000, 1)})

    if args.json:
        _json_dump(checks)
    else:
        print(f"{SERVER_NAME} {SERVER_VERSION}")
        print(f"configuration: {checks['configuration']}")
        print(f"api key: {'configured' if checks['api_key_configured'] else 'missing'}")
        print(f"endpoint: {checks['base_url']}")
        print(f"model: {checks['model']}")
        if args.live:
            print(f"live: ok ({checks['latency_ms']} ms)")
    return 0


def _evaluate_cli(args: argparse.Namespace) -> int:
    try:
        if args.input == "-":
            document = json.load(sys.stdin)
        else:
            with open(args.input, encoding="utf-8") as stream:
                document = json.load(stream)
        response = TypeSafeClient().evaluate(document)
    except (OSError, json.JSONDecodeError, BridgeError) as exc:
        print(f"evaluate: {exc}", file=sys.stderr)
        return 1
    _json_dump(response)
    return 0


def _setup_cli(args: argparse.Namespace) -> int:
    from .host_setup import run_setup

    return run_setup(
        args.host,
        detect=args.detect,
        dry_run=args.dry_run,
        remove=args.remove,
        yes=args.yes,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arbitype",
        description="Typed decision tools for AI agents, powered by TypeSafe Jev.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {SERVER_VERSION}")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="validate local configuration")
    doctor.add_argument("--json", action="store_true", help="print machine-readable output")
    doctor.add_argument("--live", action="store_true", help="make one small paid API request")

    evaluate = subparsers.add_parser("evaluate", help="evaluate one JSON request outside MCP")
    evaluate.add_argument(
        "--input",
        default="-",
        help="JSON file to read; use - for stdin (default)",
    )

    setup = subparsers.add_parser(
        "setup",
        help="safely configure Arbitype in an MCP host",
        description=(
            "Add or remove an Arbitype STDIO entry without writing API keys. "
            "Existing unknown configuration is never overwritten."
        ),
    )
    setup.add_argument(
        "host",
        nargs="?",
        choices=("codex", "claude", "cursor", "vscode"),
        help="host to configure; omit when using --detect",
    )
    setup.add_argument(
        "--detect",
        action="store_true",
        help="configure every detected supported host",
    )
    setup.add_argument(
        "--dry-run",
        action="store_true",
        help="show the plan without changing files",
    )
    setup.add_argument(
        "--remove",
        action="store_true",
        help="remove only an Arbitype entry previously managed by this command",
    )
    setup.add_argument(
        "--yes",
        action="store_true",
        help="apply without an interactive confirmation (required in non-interactive use)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor(args)
    if args.command == "evaluate":
        return _evaluate_cli(args)
    if args.command == "setup":
        return _setup_cli(args)
    return main_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
