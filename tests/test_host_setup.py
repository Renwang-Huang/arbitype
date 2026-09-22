import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arbitype import host_setup  # noqa: E402
from arbitype.host_setup import run_setup  # noqa: E402


class HostSetupTests(unittest.TestCase):
    def test_dry_run_does_not_create_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            output = StringIO()
            with redirect_stdout(output):
                result = run_setup("cursor", dry_run=True, home=home)
            self.assertEqual(result, 0)
            path = home / ".cursor" / "mcp.json"
            self.assertFalse(path.exists())
            self.assertIn("dry-run: no files changed", output.getvalue())

    def test_json_setup_is_idempotent_and_never_writes_secret(self):
        secret = "not-written-secret"
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ", {"TYPESAFE_API_KEY": secret}, clear=False
        ):
            home = Path(directory)
            self.assertEqual(run_setup("cursor", home=home), 0)
            path = home / ".cursor" / "mcp.json"
            sidecar = home / ".cursor" / ".mcp.json.arbitype-managed.json"
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(secret, content)
            self.assertEqual(json.loads(content)["mcpServers"]["arbitype"]["env"]["TYPESAFE_API_KEY"], "${env:TYPESAFE_API_KEY}")
            self.assertTrue(sidecar.exists())

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(run_setup("cursor", home=home), 0)
            self.assertIn("already configured", output.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_existing_json_server_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / ".cursor" / "mcp.json"
            path.parent.mkdir(parents=True)
            original = {"mcpServers": {"arbitype": {"command": "python", "args": ["other.py"]}}}
            path.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(run_setup("cursor", home=home), 1)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    def test_remove_only_removes_owned_json_entry_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / ".cursor" / "mcp.json"
            self.assertEqual(run_setup("cursor", home=home), 0)
            self.assertEqual(run_setup("cursor", remove=True, home=home), 0)
            self.assertNotIn("arbitype", json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {}))
            self.assertFalse((path.parent / ".mcp.json.arbitype-managed.json").exists())
            self.assertTrue(list(path.parent.glob("mcp.json.arbitype-backup-*")))

    def test_codex_setup_uses_env_vars_and_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".codex" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('[profiles.default]\nmodel = "test"\n', encoding="utf-8")
            self.assertEqual(run_setup("codex", home=home), 0)
            content = config.read_text(encoding="utf-8")
            self.assertIn("[mcp_servers.arbitype]", content)
            self.assertIn('env_vars = ["TYPESAFE_API_KEY"]', content)
            self.assertIn("BEGIN ARBITYPE MANAGED", content)
            self.assertEqual(run_setup("codex", remove=True, home=home), 0)
            self.assertNotIn("[mcp_servers.arbitype]", config.read_text(encoding="utf-8"))

    def test_vscode_setup_uses_password_input_not_a_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("arbitype.host_setup._vscode_path", return_value=home / ".config" / "Code" / "User" / "mcp.json"):
                self.assertEqual(run_setup("vscode", home=home), 0)
            path = home / ".config" / "Code" / "User" / "mcp.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["servers"]["arbitype"]["env"]["TYPESAFE_API_KEY"], "${input:typesafe-api-key}")
            self.assertTrue(data["inputs"][0]["password"])

    def test_atomic_write_has_a_windows_permission_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            host_setup.os, "fchmod", None, create=True
        ):
            home = Path(directory)
            self.assertEqual(run_setup("cursor", home=home), 0)
            self.assertTrue((home / ".cursor" / "mcp.json").exists())


if __name__ == "__main__":
    unittest.main()
