"""Compatibility package for the pre-0.4.0 ``typesafe_codex_mcp`` name.

Use :mod:`typesafe_mcp` for new integrations. The old import path remains so
existing applications can migrate without a synchronized upgrade.
"""

from typesafe_mcp import *  # noqa: F401,F403
