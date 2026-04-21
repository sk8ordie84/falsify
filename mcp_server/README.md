# falsify MCP server

A Model Context Protocol server that exposes the Falsification
Engine verdict store to any MCP-compatible client — Claude
Desktop, Claude Code, custom integrations.

**READ-ONLY.** Surfaces verdicts, claim status, and aggregate
stats. Never writes to disk.

## Install

```bash
pip install -e ".[mcp]"
```

This pulls in `mcp>=1.0.0` alongside the core `falsify` package.
The MCP SDK is an *optional* extra; falsify itself works without
it.

## Run standalone

```bash
python -m mcp_server
```

Speaks MCP over stdio. Pipe it to a client, or wire it up via
Claude Desktop config below.

## Wire into Claude Desktop

Merge the snippet from
[`claude_desktop_config.example.json`](claude_desktop_config.example.json)
into your Claude Desktop config:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Update `cwd` to point at your local clone of this repo, then
restart Claude Desktop. `falsify-verdict-log` will appear in the
MCP servers panel.

## Tools

| Tool            | Args                       | Returns                                                     |
|-----------------|----------------------------|-------------------------------------------------------------|
| `list_verdicts` | none                       | `[{name, state, metric_value, sample_size, last_run_timestamp}, ...]` |
| `get_verdict`   | `claim_name: str`          | the full `verdict.json` payload, or `{"error": "not found"}` |
| `get_stats`     | none                       | `{total, pass, fail, inconclusive, stale, unrun}`           |
| `check_claim`   | `claim_name: str`          | `{locked: bool, hash: str | null, latest_run: dict | null}` |

## Resources

| URI                           | Body                                        |
|-------------------------------|---------------------------------------------|
| `falsify://verdicts`          | JSON list of every claim's verdict row      |
| `falsify://verdicts/<claim>`  | one claim's verdict.json                    |
| `falsify://stats`             | aggregate counts                            |

## Graceful fallback

If the `mcp` package isn't installed, `python -m mcp_server` exits
with a clear message:

> MCP SDK not installed. Install with: pip install -e '.[mcp]'

The four tool functions stay importable as plain Python:

```python
from mcp_server import list_verdicts, get_stats
print(list_verdicts())
```

So unit tests and ad-hoc scripts can use them without the SDK.

## Non-goals

- **No writes.** The server will never call `lock`, `run`, or
  modify `verdict.json`. Verdict refresh is the
  `verdict-refresher` subagent's job.
- **No remote artifact backends.** S3/GCS sync is on the 0.2.x
  roadmap — see [`../ROADMAP.md`](../ROADMAP.md).
