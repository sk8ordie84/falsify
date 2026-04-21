"""MCP server exposing the Falsification Engine verdict store.

READ-ONLY. The four tool functions (`list_verdicts`, `get_verdict`,
`get_stats`, `check_claim`) are plain Python and importable without
the `mcp` SDK installed — handy for unit tests and standalone use.
The SDK adapter is lazy: the module imports cleanly without `mcp`,
but `main()` and `_build_mcp_server()` exit / raise with a helpful
message when the SDK is absent.

Install with: ``pip install -e '.[mcp]'``
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Make the top-level falsify module importable regardless of how the
# server is launched (script vs `python -m mcp_server`).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import falsify  # noqa: E402  (after sys.path shim)

SERVER_NAME = "falsify-verdict-log"
SERVER_VERSION = falsify.__version__
FALSIFY_DIR = falsify.FALSIFY_DIR

TOOL_NAMES = ["list_verdicts", "get_verdict", "get_stats", "check_claim"]
RESOURCE_URIS = (
    "falsify://verdicts",
    "falsify://verdicts/<claim>",
    "falsify://stats",
)


# ---------------------------------------------------------------------------
# Plain tool functions — no SDK dependency, callable from unit tests.
# ---------------------------------------------------------------------------


def list_verdicts() -> list[dict]:
    """Return one row per claim with state, metric value, sample size,
    and last-run timestamp."""
    rows = falsify._gather_stats_rows(FALSIFY_DIR, name_filter=None)
    return [
        {
            "name": r["name"],
            "state": r["state"],
            "metric_value": r["value"],
            "sample_size": r["n"],
            "last_run_timestamp": r["last_run_iso"],
        }
        for r in rows
    ]


def get_verdict(claim_name: str) -> dict:
    """Return the parsed verdict.json for `claim_name`, or
    `{"error": "not found"}` if the claim has no verdict on disk."""
    verdict_path = FALSIFY_DIR / claim_name / "verdict.json"
    if not verdict_path.exists():
        return {"error": "not found"}
    try:
        return json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return {"error": f"failed to read: {e}"}


def get_stats() -> dict:
    """Return aggregate counts: total + per-state breakdown."""
    rows = falsify._gather_stats_rows(FALSIFY_DIR, name_filter=None)
    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        state = r["state"]
        key = state if state in counts else "UNRUN"
        counts[key] += 1
    return {
        "total": len(rows),
        "pass": counts["PASS"],
        "fail": counts["FAIL"],
        "inconclusive": counts["INCONCLUSIVE"],
        "stale": counts["STALE"],
        "unrun": counts["UNRUN"],
    }


def check_claim(claim_name: str) -> dict:
    """Return `{locked, hash, latest_run}` for a claim by name.

    `locked` is True iff `.falsify/<name>/spec.lock.json` exists.
    `hash` is the spec_hash from that lock (or None).
    `latest_run` is the parsed run_meta.json of the latest run with
    a `run_id` field added (or None if no runs exist).
    """
    claim_dir = FALSIFY_DIR / claim_name
    spec_path = claim_dir / "spec.yaml"
    lock_path = claim_dir / "spec.lock.json"

    if not spec_path.exists():
        return {
            "locked": False,
            "hash": None,
            "latest_run": None,
            "error": "claim not found",
        }

    spec_hash: str | None = None
    locked = lock_path.exists()
    if locked:
        try:
            lock_data = json.loads(lock_path.read_text())
            h = lock_data.get("spec_hash")
            if isinstance(h, str):
                spec_hash = h
        except (OSError, json.JSONDecodeError):
            pass

    latest_run: dict | None = None
    run_dir = falsify._resolve_latest_run(claim_dir)
    if run_dir is not None and run_dir.exists():
        meta_path = run_dir / "run_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                if isinstance(meta, dict):
                    meta["run_id"] = run_dir.name
                    latest_run = meta
            except (OSError, json.JSONDecodeError):
                pass

    return {"locked": locked, "hash": spec_hash, "latest_run": latest_run}


TOOLS = {
    "list_verdicts": list_verdicts,
    "get_verdict": get_verdict,
    "get_stats": get_stats,
    "check_claim": check_claim,
}


# ---------------------------------------------------------------------------
# MCP SDK adapter — lazy. Module import succeeds without `mcp` installed;
# `_build_mcp_server` and `main` raise / exit with a clear message.
# ---------------------------------------------------------------------------


def _import_sdk():
    """Import the mcp SDK or return None.

    Returns a tuple ``(Server, stdio_server, types)`` on success, or
    ``None`` if the SDK is not installed. Callers decide what to do
    with that — `main` exits 2, `_build_mcp_server` raises.
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        import mcp.types as types  # type: ignore
    except ImportError:
        return None
    return Server, stdio_server, types


def _build_mcp_server():
    """Construct a Server with tools and resources registered."""
    sdk = _import_sdk()
    if sdk is None:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install -e '.[mcp]'"
        )
    Server, _stdio, types = sdk

    server = Server(SERVER_NAME)

    @server.list_tools()
    async def _list_tools() -> list:  # type: ignore[no-untyped-def]
        return [
            types.Tool(
                name="list_verdicts",
                description=(
                    "List every locked claim with state, metric value, "
                    "sample size, and last-run timestamp."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="get_verdict",
                description=(
                    "Return the full verdict.json for a specific claim."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim_name": {"type": "string"},
                    },
                    "required": ["claim_name"],
                },
            ),
            types.Tool(
                name="get_stats",
                description=(
                    "Aggregate counts across all claims: "
                    "total / pass / fail / inconclusive / stale / unrun."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="check_claim",
                description=(
                    "Inspect a claim by name: locked status, spec hash, "
                    "and latest run metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "claim_name": {"type": "string"},
                    },
                    "required": ["claim_name"],
                },
            ),
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]):  # type: ignore[no-untyped-def]
        if name == "list_verdicts":
            payload: Any = list_verdicts()
        elif name == "get_verdict":
            payload = get_verdict(str(arguments.get("claim_name", "")))
        elif name == "get_stats":
            payload = get_stats()
        elif name == "check_claim":
            payload = check_claim(str(arguments.get("claim_name", "")))
        else:
            payload = {"error": f"unknown tool: {name}"}
        return [
            types.TextContent(
                type="text",
                text=json.dumps(payload, indent=2, sort_keys=True),
            )
        ]

    @server.list_resources()
    async def _list_resources():  # type: ignore[no-untyped-def]
        return [
            types.Resource(
                uri="falsify://verdicts",
                name="All verdicts",
                description="JSON list of every claim's current verdict row.",
                mimeType="application/json",
            ),
            types.Resource(
                uri="falsify://stats",
                name="Aggregate stats",
                description="Summary counts across all claims.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def _read_resource(uri):  # type: ignore[no-untyped-def]
        uri_str = str(uri)
        if uri_str == "falsify://verdicts":
            return json.dumps(list_verdicts(), indent=2, sort_keys=True)
        if uri_str == "falsify://stats":
            return json.dumps(get_stats(), indent=2, sort_keys=True)
        if uri_str.startswith("falsify://verdicts/"):
            name = uri_str[len("falsify://verdicts/") :]
            return json.dumps(get_verdict(name), indent=2, sort_keys=True)
        return json.dumps(
            {"error": f"unknown resource: {uri_str}"}, indent=2, sort_keys=True
        )

    return server


def main() -> int:
    """Run the MCP server over stdio. Exits 2 if the SDK is missing."""
    sdk = _import_sdk()
    if sdk is None:
        print(
            "MCP SDK not installed. Install with: pip install -e '.[mcp]'",
            file=sys.stderr,
        )
        sys.exit(2)
    _Server, stdio_server, _types = sdk

    server = _build_mcp_server()

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    main()
