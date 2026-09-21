"""Compatibility metadata for older pip/setuptools versions."""

import re
import shutil
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py


_VERSION_FILE = Path(__file__).resolve().parent / "typesafe_mcp" / "_version.py"
_VERSION_MATCH = re.search(
    r'^__version__\s*=\s*[\"\']([^\"\']+)[\"\']\s*$',
    _VERSION_FILE.read_text(encoding="utf-8"),
    re.MULTILINE,
)
if _VERSION_MATCH is None:
    raise RuntimeError(f"could not read package version from {_VERSION_FILE}")
__version__ = _VERSION_MATCH.group(1)


class BuildPyWithoutBytecode(_build_py):
    """Keep local test bytecode out of source distributions and wheels."""

    def run(self):
        if self.build_lib and Path(self.build_lib).exists():
            shutil.rmtree(self.build_lib)
        super().run()
        for cache_dir in Path(self.build_lib).rglob("__pycache__"):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
        for bytecode in Path(self.build_lib).rglob("*.pyc"):
            if bytecode.is_file():
                bytecode.unlink()


setup(
    name="typesafe-mcp",
    version=__version__,
    description="A dependency-free, host-neutral TypeSafe AI MCP service",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="TypeSafe MCP contributors",
    author_email="renwang-huang@users.noreply.github.com",
    url="https://github.com/Renwang-Huang/typesafe-mcp",
    project_urls={
        "Issues": "https://github.com/Renwang-Huang/typesafe-mcp/issues",
        "Changelog": "https://github.com/Renwang-Huang/typesafe-mcp/blob/main/CHANGELOG.md",
    },
    python_requires=">=3.10",
    license="MIT",
    packages=find_packages(include=["typesafe_mcp", "typesafe_mcp.*", "typesafe_codex_mcp", "typesafe_codex_mcp.*"]),
    exclude_package_data={"": ["__pycache__", "__pycache__/*", "*.py[cod]"]},
    cmdclass={"build_py": BuildPyWithoutBytecode},
    entry_points={
        "console_scripts": [
            "typesafe-mcp=typesafe_mcp.cli:main",
            "typesafe-codex-mcp=typesafe_mcp.cli:main",
        ]
    },
)
