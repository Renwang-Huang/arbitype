import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMigrationPolicyTests(unittest.TestCase):
    def test_safe_manual_migration_is_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "REGISTRY_MIGRATION.md").read_text(encoding="utf-8")
        for text in (readme, docs):
            self.assertIn("python -m pip uninstall typesafe-mcp", text)
            self.assertIn("python -m pip install arbitype", text)

    def test_no_legacy_pypi_publisher_is_configured(self):
        self.assertFalse((ROOT / ".github" / "workflows" / "publish-legacy-pypi.yml").exists())
        self.assertFalse((ROOT / "compat" / "typesafe-mcp").exists())
