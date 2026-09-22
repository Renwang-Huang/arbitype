import json
import unittest
from pathlib import Path

from arbitype._version import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMigrationPolicyTests(unittest.TestCase):
    def test_release_metadata_targets_arbitype_070(self):
        self.assertEqual(__version__, "0.7.0")
        metadata = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["version"], __version__)
        self.assertEqual(metadata["packages"][0]["version"], __version__)

    def test_safe_manual_migration_is_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "REGISTRY_MIGRATION.md").read_text(encoding="utf-8")
        for text in (readme, docs):
            self.assertIn("python -m pip uninstall typesafe-mcp", text)
            self.assertIn("python -m pip install arbitype", text)

    def test_no_legacy_pypi_publisher_is_configured(self):
        self.assertFalse((ROOT / ".github" / "workflows" / "publish-legacy-pypi.yml").exists())
        self.assertFalse((ROOT / "compat" / "typesafe-mcp").exists())

    def test_registry_description_stays_within_official_limit(self):
        metadata = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
        self.assertLessEqual(len(metadata["description"]), 100)
