#!/usr/bin/env python3
"""Run the deterministic checks required before the Arbitype release tag."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arbitype._version import __version__  # noqa: E402


CANONICAL_FILES = (
    ROOT / "server.json",
    ROOT / "pyproject.toml",
    ROOT / "setup.py",
    ROOT / ".github" / "workflows" / "publish.yml",
    ROOT / ".github" / "workflows" / "publish-mcp.yml",
    ROOT / ".github" / "workflows" / "ci.yml",
)
CHECK_PATHS = (
    "arbitype",
    "typesafe_mcp",
    "typesafe_codex_mcp",
    "server.py",
    "smoke_test.py",
    "scripts",
    "tests",
)


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def check_clean_worktree(*, allow_dirty: bool) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout and not allow_dirty:
        raise RuntimeError(
            "working tree is not clean; commit release changes first or use --allow-dirty"
        )
    if result.stdout:
        print("WARNING: release readiness is running with a dirty working tree.")


def check_identity_consistency(version: str) -> None:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    if server.get("name") != "io.github.Renwang-Huang/arbitype":
        raise RuntimeError("server.json has the wrong MCP Registry identity")
    if server.get("version") != version:
        raise RuntimeError("server.json version does not match arbitype/_version.py")
    package = server.get("packages", [{}])[0]
    if package.get("identifier") != "arbitype" or package.get("version") != version:
        raise RuntimeError("server.json package metadata is inconsistent")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'name = "arbitype"' not in pyproject:
        raise RuntimeError("pyproject.toml does not declare arbitype")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    marker = "<!-- mcp-name: io.github.Renwang-Huang/arbitype -->"
    if readme.count(marker) != 1:
        raise RuntimeError("README must contain exactly one canonical mcp-name marker")
    for command in (
        "python -m pip uninstall typesafe-mcp",
        "python -m pip install arbitype",
    ):
        if command not in readme:
            raise RuntimeError(f"README is missing the safe legacy migration command: {command}")

    for path in CANONICAL_FILES:
        text = path.read_text(encoding="utf-8")
        if "Renwang-Huang/typesafe-mcp" in text:
            raise RuntimeError(f"legacy repository URL remains in canonical file {path}")
        if re.search(r"io\.github\.Renwang-Huang/Arbitype|Renwang-Huang/Arbitype", text):
            raise RuntimeError(f"non-canonical Arbitype casing remains in {path}")


def wheel_in_directory(directory: Path, prefix: str) -> Path:
    wheels = sorted(directory.glob(f"{prefix}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one {prefix} wheel in {directory}, found {wheels}")
    return wheels[0]


def inspect_canonical_wheel(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
        required = {
            "arbitype/__init__.py",
            "typesafe_mcp/__init__.py",
            "typesafe_codex_mcp/__init__.py",
        }
        missing = required - names
        if missing:
            raise RuntimeError(f"canonical wheel is missing compatibility files: {sorted(missing)}")
        bad = [name for name in names if "__pycache__" in name or name.endswith(".pyc")]
        if bad:
            raise RuntimeError(f"canonical wheel contains bytecode: {bad}")


def run_ruff() -> None:
    ruff = shutil.which("ruff")
    if ruff:
        run([ruff, "check", *CHECK_PATHS])
        return
    uvx = shutil.which("uvx")
    if uvx:
        run([uvx, "--from", "ruff>=0.8,<1", "ruff", "check", *CHECK_PATHS])
        return
    raise RuntimeError("ruff is unavailable; install ruff or uv before release-check")


def run_release_checks(*, skip_sdk: bool) -> None:
    version = __version__
    check_identity_consistency(version)
    run([sys.executable, "scripts/validate_registry_metadata.py", "--version", version])
    run([sys.executable, "scripts/validate_eval_datasets.py"])

    with tempfile.TemporaryDirectory(prefix="arbitype-release-check-") as temporary:
        temporary_root = Path(temporary)
        canonical_dist = temporary_root / "canonical-dist"
        canonical_dist.mkdir()
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                ".",
                "--wheel-dir",
                str(canonical_dist),
            ]
        )
        canonical_wheel = wheel_in_directory(canonical_dist, "arbitype")
        inspect_canonical_wheel(canonical_wheel)

    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run_ruff()
    if skip_sdk:
        print("SKIP: official MCP SDK smoke test was disabled with --skip-sdk")
    elif importlib.util.find_spec("mcp") is None:
        raise RuntimeError(
            "official MCP SDK is not installed; install 'mcp[cli]>=2,<3' or use --skip-sdk"
        )
    else:
        run([sys.executable, "scripts/official_sdk_smoke.py"])
    print(f"RELEASE READY CHECKS PASSED for Arbitype {version}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow local changes; the default release check requires a clean tree",
    )
    parser.add_argument(
        "--skip-sdk",
        action="store_true",
        help="skip the official MCP SDK smoke test when its dev dependency is unavailable",
    )
    args = parser.parse_args(argv)
    try:
        check_clean_worktree(allow_dirty=args.allow_dirty)
        run_release_checks(skip_sdk=args.skip_sdk)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"RELEASE NOT READY: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
