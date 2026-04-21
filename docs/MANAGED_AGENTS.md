# Managed Agents deployment

Falsification Engine ships two Managed Agent configs
([`managed_agents/`](../managed_agents/)) that deploy the subagents
to Anthropic's Console for scheduled and on-demand execution.

## Why

The `verdict-refresher` agent benefits from running on a schedule
(every 6 hours) without needing a developer machine open. The
`claim-auditor` agent benefits from being a stable URL you can
invoke from a CI webhook on every PR.

## Prerequisites

- Anthropic Console access — <https://console.anthropic.com>.
- API credits on the account (the agents consume tokens per run).
- This repo cloned to the account's deploy target (git connection
  configured in Console).

## Deploy `verdict-refresher` (scheduled)

1. Console → Agents → **Create new agent**.
2. Import [`managed_agents/verdict-refresher.yaml`](../managed_agents/verdict-refresher.yaml).
3. Connect the repo.
4. Save. The agent starts running every 6 hours.
5. View run history in Console; scheduled summaries post as
   agent-run artifacts.

## Deploy `claim-auditor` (on-demand)

1. Console → Agents → **Create new agent**.
2. Import [`managed_agents/claim-auditor.yaml`](../managed_agents/claim-auditor.yaml).
3. Connect the repo.
4. Save. The agent exposes a webhook URL.
5. POST `{"text": "..."}` to the webhook; response is the markdown
   audit table.

## Cost expectations

Approximate token usage per run:

| Agent               | Tokens / run | Trigger            |
|---------------------|--------------|--------------------|
| `verdict-refresher` | 2–10k        | cron, every 6h     |
| `claim-auditor`     | 1–5k         | on-demand webhook  |

At the default 6-hour schedule, `verdict-refresher` costs roughly
*X credits / day* — replace `X` after the first week of real
billing data.

## Rollback

Disable the agent in Console; no local state to clean up. Specs
and verdicts remain on disk regardless of agent state. To
re-enable, flip the agent back on — the manifest is idempotent.

## Security

Both agents are tools-limited: only `bash` with `falsify`
subcommand access. Neither agent can exfiltrate secrets, modify
specs, or write to anything beyond `.falsify/<name>/runs/` and
`verdict.json`. Repo credentials are handled by Console, not
embedded in the manifests — the YAML files are safe to commit to
a public repo.

## Alignment with subagents

These Managed Agent manifests mirror the local subagents at
[`.claude/agents/claim-auditor.md`](../.claude/agents/claim-auditor.md)
and
[`.claude/agents/verdict-refresher.md`](../.claude/agents/verdict-refresher.md).
The local versions run in your Claude Code session; the Managed
versions run in the cloud on schedule or on demand. Same logic,
different execution surface.
