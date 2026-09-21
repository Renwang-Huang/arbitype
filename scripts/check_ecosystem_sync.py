#!/usr/bin/env python3
"""Check that public MCP directories reflect the current published version."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# Running ``python scripts/...`` puts ``scripts/`` first on sys.path. Add the
# repository root so this check works both locally and in GitHub Actions.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arbitype._version import __version__  # noqa: E402


SERVER_NAME = "io.github.Renwang-Huang/arbitype"
REPOSITORY_URL = "https://github.com/Renwang-Huang/arbitype"
GLAMA_URL = "https://glama.ai/mcp/servers/Renwang-Huang/arbitype"


def fetch(url: str) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "arbitype-ecosystem-check"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise RuntimeError(f"request failed for {url}: {exc.reason}") from exc


def check_registry(version: str, *, strict: bool) -> list[str]:
    url = (
        "https://registry.modelcontextprotocol.io/v0.1/servers/"
        f"{quote(SERVER_NAME, safe='')}/versions/latest"
    )
    status, body = fetch(url)
    if status == 404 and not strict:
        print(
            "::warning::Arbitype is not published in the official MCP Registry yet; "
            "the post-release verification will require it."
        )
        return []
    if status != 200:
        return [f"official MCP Registry returned HTTP {status} for {SERVER_NAME}"]

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return [f"official MCP Registry returned invalid JSON: {exc}"]

    server = payload.get("server", {})
    if server.get("name") != SERVER_NAME:
        return ["official MCP Registry returned an unexpected server name"]
    if server.get("version") != version:
        return [
            "official MCP Registry is not current: "
            f"expected {version}, found {server.get('version')}"
        ]

    print(f"official MCP Registry: {SERVER_NAME} {version}")
    return []


def check_glama(version: str, *, strict: bool) -> list[str]:
    status, body = fetch(GLAMA_URL)
    if status == 404 and not strict:
        print(
            "::warning::Arbitype is not visible on Glama yet; Glama controls "
            "the crawl schedule after the repository rename."
        )
        return []
    if status != 200:
        return [f"Glama returned HTTP {status} for {GLAMA_URL}"]

    page = body.decode("utf-8", errors="replace")
    if REPOSITORY_URL not in page:
        if not strict:
            print("::warning::Glama does not show the renamed Arbitype repository yet.")
            return []
        return ["Glama listing does not point to the canonical GitHub repository"]

    # Glama owns the crawl schedule. A lagging README/tool snapshot should be
    # visible in Actions without making releases fail solely on Glama timing.
    if f"v{version}" not in page and f"=={version}" not in page:
        print(
            f"::warning::Glama listing is reachable but may still be behind {version}; "
            "Glama controls repository re-sync timing."
        )
    else:
        print(f"Glama: listing contains published version {version}")
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=__version__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail when the new Registry or Glama listing is not visible",
    )
    args = parser.parse_args()

    errors = check_registry(args.version, strict=args.strict) + check_glama(
        args.version, strict=args.strict
    )
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
