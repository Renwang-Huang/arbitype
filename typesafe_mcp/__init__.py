"""Legacy compatibility package for the former TypeSafe MCP import path.

Use :mod:`arbitype` for new integrations. The module aliases below keep
patching and identity checks pointed at the one canonical implementation.
"""

import sys as _sys

import arbitype as _arbitype
from arbitype import *  # noqa: F401,F403
from arbitype import _version as _version
from arbitype import cli as cli
from arbitype import core as core
from arbitype import mcp as mcp

__version__ = _arbitype.__version__

_sys.modules[__name__ + ".cli"] = cli
_sys.modules[__name__ + ".core"] = core
_sys.modules[__name__ + ".mcp"] = mcp
_sys.modules[__name__ + "._version"] = _version

__all__ = [*getattr(_arbitype, "__all__", ()), "cli", "core", "mcp"]
