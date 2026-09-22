"""Safe, host-aware MCP configuration for Arbitype.

The setup command intentionally writes only a small, recognizable Arbitype
entry. It never writes ``TYPESAFE_API_KEY`` values, replaces an existing
server with the same name, or removes configuration it cannot prove it owns.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import tempfile
from difflib import unified_diff
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOST_NAMES = ("codex", "claude", "cursor", "vscode")
SERVER_NAME = "arbitype"
ENVIRONMENT_VARIABLE = "TYPESAFE_API_KEY"
MANAGED_BEGIN = "# BEGIN ARBITYPE MANAGED MCP SERVER"
MANAGED_END = "# END ARBITYPE MANAGED MCP SERVER"


class SetupError(RuntimeError):
    """Raised when a host configuration is unsafe to inspect or update."""


@dataclass(frozen=True)
class HostSpec:
    name: str
    path: Path
    format: str
    root_key: str | None
    detected: bool
    detection_reason: str


@dataclass
class SetupPlan:
    spec: HostSpec
    action: str
    message: str
    content: str | None = None
    sidecar_content: str | None = None
    remove_sidecar: bool = False
    backup_required: bool = False
    original_content: str | None = None


def _command_available(*commands: str) -> bool:
    return any(shutil.which(command) for command in commands)


def _vscode_path(home: Path) -> Path:
    system = platform.system()
    if system == "Darwin":
        candidates = (
            home / "Library" / "Application Support" / "Code" / "User" / "mcp.json",
            home / "Library" / "Application Support" / "Code - Insiders" / "User" / "mcp.json",
        )
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        candidates = (
            appdata / "Code" / "User" / "mcp.json",
            appdata / "Code - Insiders" / "User" / "mcp.json",
        )
    else:
        candidates = (
            home / ".config" / "Code" / "User" / "mcp.json",
            home / ".config" / "Code - Insiders" / "User" / "mcp.json",
        )
    return next((path for path in candidates if path.exists()), candidates[0])


def _claude_path(home: Path) -> tuple[Path, str]:
    """Prefer Claude Code's documented user config, then an existing Desktop file."""

    code_path = home / ".claude.json"
    if _command_available("claude") or code_path.exists():
        return code_path, "claude-code"

    system = platform.system()
    if system == "Darwin":
        desktop = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        desktop = appdata / "Claude" / "claude_desktop_config.json"
    else:
        desktop = home / ".config" / "Claude" / "claude_desktop_config.json"
    if desktop.exists():
        return desktop, "claude-desktop"
    return code_path, "claude-code"


def host_specs(*, home: Path | None = None) -> dict[str, HostSpec]:
    """Return host paths using the platform's documented user locations."""

    home = home or Path.home()
    claude_path, claude_kind = _claude_path(home)
    codex_path = home / ".codex" / "config.toml"
    cursor_path = home / ".cursor" / "mcp.json"
    vscode_path = _vscode_path(home)
    return {
        "codex": HostSpec(
            "codex",
            codex_path,
            "toml",
            None,
            _command_available("codex") or codex_path.exists(),
            "codex executable or ~/.codex/config.toml exists",
        ),
        "claude": HostSpec(
            "claude",
            claude_path,
            "json-mcpServers",
            "mcpServers",
            _command_available("claude") or claude_path.exists(),
            f"Claude Code executable or {claude_kind} configuration exists",
        ),
        "cursor": HostSpec(
            "cursor",
            cursor_path,
            "json-mcpServers",
            "mcpServers",
            _command_available("cursor") or cursor_path.exists(),
            "cursor executable or ~/.cursor/mcp.json exists",
        ),
        "vscode": HostSpec(
            "vscode",
            vscode_path,
            "json-servers",
            "servers",
            _command_available("code") or vscode_path.exists(),
            "code executable or the VS Code user MCP configuration exists",
        ),
    }


def _server_entry(host: str) -> dict[str, Any]:
    if host == "claude":
        # Claude Code documents ${VAR} expansion in command, args, and env.
        environment = {ENVIRONMENT_VARIABLE: "${TYPESAFE_API_KEY}"}
    elif host == "cursor":
        # Cursor documents the ${env:NAME} interpolation syntax.
        environment = {ENVIRONMENT_VARIABLE: "${env:TYPESAFE_API_KEY}"}
    elif host == "vscode":
        # VS Code prompts for password inputs and does not persist the value.
        environment = {ENVIRONMENT_VARIABLE: "${input:typesafe-api-key}"}
    else:
        raise SetupError(f"unsupported JSON host: {host}")

    return {
        "type": "stdio",
        "command": "uvx",
        "args": ["arbitype"],
        "env": environment,
    }


def _vscode_input() -> dict[str, Any]:
    return {
        "type": "promptString",
        "id": "typesafe-api-key",
        "description": "TypeSafe API key for Arbitype",
        "password": True,
    }


def _sidecar_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.arbitype-managed.json")


def _expected_toml_block() -> str:
    return "\n".join(
        (
            MANAGED_BEGIN,
            "[mcp_servers.arbitype]",
            'command = "uvx"',
            'args = ["arbitype"]',
            'env_vars = ["TYPESAFE_API_KEY"]',
            MANAGED_END,
        )
    )


def _toml_section_pattern() -> re.Pattern[str]:
    return re.compile(r"(?m)^\[mcp_servers\.(?:arbitype|\"arbitype\")\]\s*$")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"{path} is not valid UTF-8; refusing to modify it") from exc


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {}, False
    try:
        value = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        raise SetupError(f"{path} is not valid JSON; refusing to modify it") from exc
    if not isinstance(value, dict):
        raise SetupError(f"{path} must contain a JSON object; refusing to modify it")
    return value, True


def _json_sidecar_is_owned(path: Path) -> bool:
    sidecar = _sidecar_path(path)
    if not sidecar.exists():
        return False
    try:
        value = json.loads(_read_text(sidecar))
    except (json.JSONDecodeError, SetupError):
        return False
    return value == {"managed_by": "arbitype", "server": SERVER_NAME, "version": 1}


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _prepare_json(spec: HostSpec, *, remove: bool) -> SetupPlan:
    original_content = _read_text(spec.path) if spec.path.exists() else ""
    data, existed = _load_json(spec.path)
    root_key = spec.root_key
    assert root_key is not None
    servers = data.get(root_key, {})
    if not isinstance(servers, dict):
        raise SetupError(f"{spec.path}: {root_key!r} must be an object")

    current = servers.get(SERVER_NAME)
    expected = _server_entry(spec.name)
    owned = _json_sidecar_is_owned(spec.path)
    if remove:
        if current is None:
            return SetupPlan(spec, "noop", "Arbitype is not configured.")
        if not owned:
            return SetupPlan(
                spec,
                "noop",
                "An Arbitype entry exists, but it is not marked as managed; refusing to remove it.",
            )
        if current != expected:
            return SetupPlan(
                spec,
                "conflict",
                "The managed entry was modified; refusing to remove user changes.",
            )
        updated = dict(data)
        updated[root_key] = dict(servers)
        del updated[root_key][SERVER_NAME]
        if not updated[root_key]:
            del updated[root_key]
        return SetupPlan(
            spec,
            "remove",
            "Remove the Arbitype entry owned by this setup command.",
            content=_json_text(updated),
            remove_sidecar=True,
            backup_required=existed,
            original_content=original_content,
        )

    if current is not None:
        if current == expected and owned:
            return SetupPlan(spec, "noop", "Arbitype is already configured and managed by Arbitype.")
        if current == expected:
            return SetupPlan(
                spec,
                "noop",
                "Arbitype is already configured; it is not managed by this command, so no changes were made.",
            )
        return SetupPlan(
            spec,
            "conflict",
            "A server named arbitype already exists; refusing to overwrite unknown configuration.",
        )

    updated = dict(data)
    updated[root_key] = dict(servers)
    updated[root_key][SERVER_NAME] = expected
    if spec.name == "vscode":
        inputs = updated.get("inputs", [])
        if not isinstance(inputs, list):
            raise SetupError(f"{spec.path}: inputs must be an array")
        if not any(isinstance(item, dict) and item.get("id") == "typesafe-api-key" for item in inputs):
            updated["inputs"] = [*inputs, _vscode_input()]
    sidecar = {"managed_by": "arbitype", "server": SERVER_NAME, "version": 1}
    return SetupPlan(
        spec,
        "add",
        "Add an Arbitype STDIO server without storing an API key.",
        content=_json_text(updated),
        sidecar_content=_json_text(sidecar),
        backup_required=existed,
        original_content=original_content,
    )


def _prepare_codex(spec: HostSpec, *, remove: bool) -> SetupPlan:
    original_content = _read_text(spec.path) if spec.path.exists() else ""
    content = original_content
    block = _expected_toml_block()
    section_exists = _toml_section_pattern().search(content) is not None
    managed_exists = block in content
    if remove:
        if not managed_exists:
            if section_exists:
                return SetupPlan(
                    spec,
                    "noop",
                    "A server named arbitype exists, but it is not marked as managed; refusing to remove it.",
                )
            return SetupPlan(spec, "noop", "Arbitype is not configured.")
        updated = content.replace(block, "").rstrip() + ("\n" if content.endswith("\n") else "")
        return SetupPlan(
            spec,
            "remove",
            "Remove the Arbitype TOML block owned by this setup command.",
            content=updated,
            backup_required=spec.path.exists(),
            original_content=original_content,
        )

    if section_exists:
        if managed_exists:
            return SetupPlan(spec, "noop", "Arbitype is already configured and managed by Arbitype.")
        return SetupPlan(
            spec,
            "conflict",
            "A [mcp_servers.arbitype] section already exists; refusing to overwrite unknown configuration.",
        )

    if content and not content.endswith("\n"):
        content += "\n"
    updated = f"{content}\n{block}\n" if content else f"{block}\n"
    return SetupPlan(
        spec,
        "add",
        "Add a marked Codex MCP block with env_vars forwarding only.",
        content=updated,
        backup_required=spec.path.exists(),
        original_content=original_content,
    )


def prepare_plan(spec: HostSpec, *, remove: bool = False) -> SetupPlan:
    if spec.format == "toml":
        return _prepare_codex(spec, remove=remove)
    return _prepare_json(spec, remove=remove)


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.arbitype-backup-{timestamp}")
    suffix = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.arbitype-backup-{timestamp}-{suffix}")
        suffix += 1
    shutil.copy2(path, backup)
    return backup


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            fchmod = getattr(os, "fchmod", None)
            if fchmod is not None:
                fchmod(stream.fileno(), mode)
            else:
                os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def apply_plan(plan: SetupPlan) -> Path | None:
    if plan.action not in {"add", "remove"} or plan.content is None:
        return None
    backup = _backup(plan.spec.path) if plan.backup_required else None
    _atomic_write(plan.spec.path, plan.content)
    sidecar = _sidecar_path(plan.spec.path)
    if plan.sidecar_content is not None:
        _atomic_write(sidecar, plan.sidecar_content)
    elif plan.remove_sidecar and sidecar.exists():
        sidecar.unlink()
    return backup


def _format_plan(plan: SetupPlan) -> str:
    lines = [f"[{plan.spec.name}] {plan.spec.path}", f"  status: {plan.action}", f"  change: {plan.message}"]
    if plan.backup_required:
        lines.append("  backup: an automatic timestamped backup will be created")
    if plan.action == "add":
        lines.append("  credential: TYPESAFE_API_KEY is referenced, never written")
    return "\n".join(lines)


def _format_diff(plan: SetupPlan) -> str:
    """Render the exact file change without exposing credentials."""

    if plan.action not in {"add", "remove"} or plan.content is None:
        return ""
    before = (plan.original_content or "").splitlines(keepends=True)
    after = plan.content.splitlines(keepends=True)
    diff = unified_diff(
        before,
        after,
        fromfile=f"{plan.spec.path} (before)",
        tofile=f"{plan.spec.path} (after)",
    )
    rendered = "".join(diff)
    return rendered if rendered else "(no file content change)\n"


def _confirm_apply(*, yes: bool) -> bool:
    if yes:
        print("confirmation: --yes supplied; applying planned changes")
        return True
    if not (os.sys.stdin.isatty() and os.sys.stdout.isatty()):
        print(
            "setup: refusing to write in a non-interactive environment; "
            "review the diff and pass --yes to apply",
            file=os.sys.stderr,
        )
        return False
    try:
        answer = input("Apply these changes? [y/N] ")
    except EOFError:
        print("setup: no confirmation received; no files changed", file=os.sys.stderr)
        return False
    if answer.strip().lower() not in {"y", "yes"}:
        print("setup: declined; no files changed")
        return False
    return True


def run_setup(
    host: str | None = None,
    *,
    detect: bool = False,
    dry_run: bool = False,
    remove: bool = False,
    yes: bool = False,
    home: Path | None = None,
) -> int:
    """Plan and optionally apply safe host configuration changes."""

    if detect and host:
        print("setup: choose a host or --detect, not both", file=os.sys.stderr)
        return 2
    if not detect and not host:
        print("setup: provide codex, claude, cursor, vscode, or --detect", file=os.sys.stderr)
        return 2
    if host and host not in HOST_NAMES:
        print(f"setup: unsupported host {host!r}; choose {', '.join(HOST_NAMES)}", file=os.sys.stderr)
        return 2

    specs = host_specs(home=home)
    selected = [name for name in HOST_NAMES if specs[name].detected] if detect else [host]
    if not selected:
        print("setup: no supported MCP host detected", file=os.sys.stderr)
        return 1

    plans: list[SetupPlan] = []
    try:
        for name in selected:
            plan = prepare_plan(specs[name], remove=remove)
            plans.append(plan)
    except SetupError as exc:
        print(f"setup: {exc}", file=os.sys.stderr)
        return 1

    print("Arbitype host setup plan")
    if detect:
        print(f"detected hosts: {', '.join(selected)}")
    for plan in plans:
        print(_format_plan(plan))

    conflicts = [plan for plan in plans if plan.action == "conflict"]
    if conflicts:
        print("setup: no files changed because an existing configuration is ambiguous", file=os.sys.stderr)
        return 1
    if dry_run:
        for plan in plans:
            diff = _format_diff(plan)
            if diff:
                print(f"Unified diff for {plan.spec.name}:")
                print(diff, end="" if diff.endswith("\n") else "\n")
        print("dry-run: no files changed")
        return 0

    changes = [plan for plan in plans if plan.action in {"add", "remove"}]
    for plan in changes:
        diff = _format_diff(plan)
        print(f"Unified diff for {plan.spec.name}:")
        print(diff, end="" if diff.endswith("\n") else "\n")
    if changes and not _confirm_apply(yes=yes):
        return 2

    backups: list[tuple[str, Path]] = []
    try:
        for plan in plans:
            backup = apply_plan(plan)
            if backup is not None:
                backups.append((plan.spec.name, backup))
    except (OSError, SetupError) as exc:
        print(f"setup: failed while writing configuration: {exc}", file=os.sys.stderr)
        return 1

    for name, backup in backups:
        print(f"{name}: backup written to {backup}")
    if any(plan.action in {"add", "remove"} for plan in plans):
        print("Verify with: arbitype doctor --json")
    else:
        print("No configuration changes were necessary.")
    return 0


__all__ = [
    "HOST_NAMES",
    "HostSpec",
    "SetupError",
    "SetupPlan",
    "host_specs",
    "prepare_plan",
    "run_setup",
]
