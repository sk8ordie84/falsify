"""MCP server exposing the Falsification Engine verdict store.

READ-ONLY. The server exposes `.falsify/*/verdict.json`,
`.falsify/*/spec.lock.json`, and the `stats` aggregate as MCP
resources, plus four tool functions (`list_verdicts`,
`get_verdict`, `get_stats`, `check_claim`). Nothing here writes to
disk — refreshing verdicts is the `verdict-refresher` subagent's
job, not this server's.

# TODO: Wire to mcp SDK — see mcp_server/README.md.
# The tool functions below are implemented and importable; only
# the `Server` / `stdio_server` bindings are stubbed for now.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the top-level falsify module importable regardless of how the
# server is launched (module vs script).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import falsify  # noqa: E402  (after sys.path shim)

SERVER_NAME = "falsify-verdict-log"
SERVER_VERSION = falsify.__version__

FALSIFY_DIR = falsify.FALSIFY_DIR

RESOURCE_URIS = (
    "falsify://verdicts",
    "falsify://verdicts/<name>",
    "falsify://specs/<name>",
    "falsify://stats",
)


# ---------------------------------------------------------------------------
# Tool implementations — pure Python, usable standalone, no RPC dependency.
# ---------------------------------------------------------------------------


def list_verdicts() -> list[dict]:
    """Return one row per claim: name, state, metric, threshold, last_run."""
    rows = falsify._gather_stats_rows(FALSIFY_DIR, name_filter=None)
    return [
        {
            "name": r["name"],
            "state": r["state"],
            "metric": r["metric"],
            "threshold": r["threshold"],
            "last_run": r["last_run_iso"],
        }
        for r in rows
    ]


def get_verdict(name: str) -> dict:
    """Return the parsed verdict.json for `name`, or an error dict."""
    verdict_path = FALSIFY_DIR / name / "verdict.json"
    if not verdict_path.exists():
        return {"error": f"no verdict for {name!r}"}
    try:
        return json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return {"error": f"failed to read {verdict_path}: {e}"}


def get_spec_lock(name: str) -> dict:
    """Return the parsed spec.lock.json for `name`, or an error dict."""
    lock_path = FALSIFY_DIR / name / "spec.lock.json"
    if not lock_path.exists():
        return {"error": f"no lock for {name!r}"}
    try:
        return json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return {"error": f"failed to read {lock_path}: {e}"}


def get_stats() -> dict:
    """Return an aggregate summary dict across all locked claims."""
    rows = falsify._gather_stats_rows(FALSIFY_DIR, name_filter=None)
    counts = {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0, "STALE": 0, "UNRUN": 0}
    for r in rows:
        state = r["state"]
        if state in counts:
            counts[state] += 1
        else:
            counts["UNRUN"] += 1
    return {"total": len(rows), **counts}


def check_claim(text: str) -> dict:
    """Run the keyword-match guard logic against locked verdicts.

    Returns a dict with two keys:
      matches        — all specs whose claim text fuzzy-matches the
                       input, regardless of state.
      contradictions — the subset of matches whose state is FAIL /
                       INCONCLUSIVE *and* the input contains at least
                       one affirmative keyword.
    """
    input_norm = falsify._normalize_text(text)
    input_tokens = set(input_norm.split())
    has_affirmative = any(
        kw in input_tokens for kw in falsify._AFFIRMATIVE_KEYWORDS
    )

    matches: list[dict] = []
    contradictions: list[dict] = []

    for claim_dir in falsify._iter_claim_dirs(FALSIFY_DIR):
        state, _ = falsify._derive_claim_state(claim_dir)
        claim_text = falsify._read_claim_text(claim_dir)
        if claim_text is None:
            continue
        if not falsify._claim_text_matches(
            falsify._normalize_text(claim_text), input_norm
        ):
            continue
        entry = {
            "name": claim_dir.name,
            "state": state,
            "claim": claim_text,
        }
        matches.append(entry)
        if has_affirmative and state in ("FAIL", "INCONCLUSIVE"):
            contradictions.append(entry)

    return {
        "matches": matches,
        "contradictions": contradictions,
        "affirmative_detected": has_affirmative,
    }


TOOLS = {
    "list_verdicts": list_verdicts,
    "get_verdict": get_verdict,
    "get_stats": get_stats,
    "check_claim": check_claim,
}


# ---------------------------------------------------------------------------
# MCP transport — STUB. The tool functions above are final; this main()
# shim will be replaced with real `Server` / `stdio_server` wiring once the
# mcp SDK version is pinned.
# ---------------------------------------------------------------------------


def main() -> int:
    try:
        import mcp  # noqa: F401
    except ImportError:
        print(
            "falsify-mcp-server: the `mcp` SDK is not installed.\n"
            "Install it with:  pip install -e '.[mcp]'\n"
            "Then re-run:      python3 -m mcp_server.server",
            file=sys.stderr,
        )
        return 1

    raise NotImplementedError(
        "MCP stdio_server wiring is pending — see mcp_server/README.md.\n"
        "The tool functions (list_verdicts, get_verdict, get_stats, "
        "check_claim) are implemented and importable; only the SDK "
        "adapter is stubbed."
    )


if __name__ == "__main__":
    sys.exit(main())
