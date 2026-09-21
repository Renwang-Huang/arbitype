"""Compatibility metadata for older pip/setuptools versions."""

import shutil
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py


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
    name="typesafe-codex-mcp",
    version="0.3.0",
    description="A dependency-free TypeSafe AI MCP service for Codex",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="TypeSafe Codex MCP contributors",
    author_email="renwang-huang@users.noreply.github.com",
    url="https://github.com/Renwang-Huang/typesafe-codex-mcp",
    project_urls={
        "Issues": "https://github.com/Renwang-Huang/typesafe-codex-mcp/issues",
        "Changelog": "https://github.com/Renwang-Huang/typesafe-codex-mcp/blob/main/CHANGELOG.md",
    },
    python_requires=">=3.10",
    license="MIT",
    packages=find_packages(include=["typesafe_codex_mcp", "typesafe_codex_mcp.*"]),
    exclude_package_data={"": ["__pycache__", "__pycache__/*", "*.py[cod]"]},
    cmdclass={"build_py": BuildPyWithoutBytecode},
    entry_points={"console_scripts": ["typesafe-codex-mcp=typesafe_codex_mcp.cli:main"]},
)
