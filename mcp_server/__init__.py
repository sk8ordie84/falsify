"""Falsification Engine MCP server package.

The four read-only tool functions are re-exported here so consumers
can call them without importing the SDK-aware ``server`` submodule:

    from mcp_server import list_verdicts, get_verdict, get_stats, check_claim

The ``Server`` adapter lives in :mod:`mcp_server.server` and is
imported lazily — only when you actually want to run the MCP server.
"""

from mcp_server.server import (
    check_claim,
    get_stats,
    get_verdict,
    list_verdicts,
)

__all__ = [
    "check_claim",
    "get_stats",
    "get_verdict",
    "list_verdicts",
]
