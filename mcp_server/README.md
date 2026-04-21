# falsify MCP server

A Model Context Protocol server that exposes the Falsification
Engine's verdict store to any MCP-compatible client — Claude
Desktop, Claude Code, or a custom integration.

**READ-ONLY.** The server surfaces verdicts, spec locks, and
aggregate stats. It does not write to disk. Refreshing verdicts is
the `verdict-refresher` subagent's job, not this server's.

## Install

The MCP SDK is an optional dependency. Install the extra:

```bash
pip install -e '.[mcp]'
```

This pulls in `mcp>=0.9.0` alongside the core `falsify` package.

## Wire into Claude Desktop

Merge the snippet in
[`claude_desktop_config.example.json`](claude_desktop_config.example.json)
into your Claude Desktop config, typically at:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Update the `cwd` path to point at your local clone of this repo.
Restart Claude Desktop; `falsify-verdict-log` will appear in the
MCP servers panel.

## Exposed resources

| URI                           | Body                                         |
|-------------------------------|----------------------------------------------|
| `falsify://verdicts`          | list of all verdict.json contents            |
| `falsify://verdicts/<name>`   | one claim's verdict.json                     |
| `falsify://specs/<name>`      | one claim's spec.lock.json                   |
| `falsify://stats`             | aggregate summary (PASS/FAIL/STALE counts)   |

## Exposed tools

| Tool            | Signature                     | Returns                                 |
|-----------------|-------------------------------|-----------------------------------------|
| `list_verdicts` | `()`                          | `[{name, state, metric, threshold, last_run}, ...]` |
| `get_verdict`   | `(name: str)`                 | the full verdict.json                   |
| `get_stats`     | `()`                          | `{total, PASS, FAIL, INCONCLUSIVE, STALE, UNRUN}` |
| `check_claim`   | `(text: str)`                 | `{matches, contradictions, affirmative_detected}` |

## Example transcripts

> **User:** what's the latest verdict for juju?
>
> **Claude** *(calls get_verdict("juju"))* → `{"verdict": "PASS", "observed_value": 0.214, "threshold": 0.25, ...}`
>
> It passed — brier 0.214 is below the 0.25 threshold, checked
> yesterday.

> **User:** does this PR description contradict anything we've
> locked?
>
> **Claude** *(calls check_claim(pr_body))* → `{"contradictions": [{"name": "retrieval-recall", "state": "FAIL", ...}]}`
>
> Yes — the PR says "retrieval recall confirmed above 85%", but
> `retrieval-recall`'s last verdict is FAIL. Block or re-run.

## Non-goals

- **No writes.** The server will never call `lock`, `run`, or
  modify `verdict.json`. If you need a fresh verdict, run the CLI
  or invoke the `verdict-refresher` subagent.
- **No network fetch.** The server only reads the local
  `.falsify/` directory. Remote artifact backends (S3, GCS) are on
  the 0.2.x roadmap.

## Status

Scaffolded in 0.1.0 (April 2026). The MCP SDK wiring is stubbed —
the four tool functions are fully implemented in Python and
importable (`from mcp_server.server import list_verdicts`), but
the `stdio_server` adapter raises `NotImplementedError` until the
SDK version is pinned. Track progress in
[ROADMAP.md](../ROADMAP.md) under the 0.2.0 target.
