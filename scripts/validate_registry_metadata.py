#!/usr/bin/env python3
"""Validate the repository metadata consumed by the official MCP Registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Running ``python scripts/...`` puts ``scripts/`` first on sys.path. Add the
# repository root so this check works both locally and in GitHub Actions.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arbitype._version import __version__  # noqa: E402


SERVER_NAME = "io.github.Renwang-Huang/arbitype"
REPOSITORY_URL = "https://github.com/Renwang-Huang/arbitype"
PACKAGE_NAME = "arbitype"
README_MARKER = f"<!-- mcp-name: {SERVER_NAME} -->"


def validate(expected_version: str) -> list[str]:
    errors: list[str] = []
    metadata_path = Path("server.json")
    readme_path = Path("README.md")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ["server.json is missing"]
    except json.JSONDecodeError as exc:
        return [f"server.json is not valid JSON: {exc}"]

    if metadata.get("name") != SERVER_NAME:
        errors.append(f"server.json name must be {SERVER_NAME!r}")
    if metadata.get("version") != expected_version:
        errors.append(
            f"server.json version must be {expected_version!r}; "
            f"found {metadata.get('version')!r}"
        )
    if metadata.get("repository", {}).get("url") != REPOSITORY_URL:
        errors.append("server.json repository URL is incorrect")

    packages = metadata.get("packages")
    if not isinstance(packages, list) or len(packages) != 1:
        errors.append("server.json must contain exactly one package")
    else:
        package = packages[0]
        expected_package = {
            "registryType": "pypi",
            "identifier": PACKAGE_NAME,
            "version": expected_version,
            "runtimeHint": "uvx",
        }
        for key, value in expected_package.items():
            if package.get(key) != value:
                errors.append(
                    f"server.json package {key!r} must be {value!r}; "
                    f"found {package.get(key)!r}"
                )
        if package.get("transport", {}).get("type") != "stdio":
            errors.append("server.json package transport must be stdio")

    try:
        readme = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append("README.md is missing")
    else:
        if README_MARKER not in readme:
            errors.append(f"README.md must contain {README_MARKER!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        default=__version__,
        help="Expected package version (defaults to the source package version).",
    )
    args = parser.parse_args()

    errors = validate(args.version)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Registry metadata is valid for {SERVER_NAME} {args.version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
