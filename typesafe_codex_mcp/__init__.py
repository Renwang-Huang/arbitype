"""Legacy compatibility package for the pre-0.4.0 import name.

This package is a shim, not a second implementation. Use :mod:`typesafe_mcp`
for all new integrations; the old import path remains for existing callers.
"""

from typesafe_mcp import *  # noqa: F401,F403
