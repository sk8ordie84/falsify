# Falsification Engine

**Pre-registration + CI for AI-agent claims.**

AI agents — and the humans who prompt them — are fluent at making claims
that sound convincing but quietly shift when reality pushes back. The
Falsification Engine borrows one idea from science: before you assert
something, write down exactly what would prove you wrong. Then let CI
watch for it.

A claim becomes an auditable contract: a short YAML file with a
hypothesis, the evidence that would falsify it, and a cryptographic lock
so the goalposts can't move after the fact.

## Why

- **Pre-registration.** Claims are hashed and locked *before* evidence is
  gathered. No retroactive edits.
- **Falsifiability, not vibes.** Every claim ships with explicit
  falsification criteria. If the criteria trigger, the claim fails —
  mechanically, not rhetorically.
- **CI-native.** `falsify guard` wraps any command and fails the build
  when a locked claim is falsified. Works in GitHub Actions, pre-commit
  hooks, or anywhere else that respects exit codes.
- **Agent-friendly.** Designed for AI agents to register their own
  claims as they work, so downstream reviewers can check whether the
  agent was right instead of relying on self-reported confidence.

## Install

Requires Python 3.11+. One dependency: `pyyaml`.

```bash
pip install pyyaml
python falsify.py --help
```

## Commands

| Command                  | Purpose                                                      |
|--------------------------|--------------------------------------------------------------|
| `init <name>`            | Scaffold a new claim spec from `examples/template.yaml`      |
| `lock <name> [--force]`  | Validate and freeze a claim (canonical YAML + SHA-256)       |
| `run <name>`             | Execute the experiment; write run artifacts under `runs/`    |
| `verdict <name>`         | Apply `failure_criteria`; report PASS/FAIL, write verdict    |
| `list [--json]`          | Table of every claim's lock/run/verdict state (or JSON)      |
| `guard`                  | Scan mode — non-zero if any claim is FAIL or STALE           |
| `guard "<text>"`         | Text mode — block affirmative claims vs non-PASS verdicts    |
| `guard -- <cmd> [args]`  | Wrap mode — run `<cmd>`; on success, fall through to scan    |

## Exit codes

| Code | Meaning                                                                |
|------|------------------------------------------------------------------------|
| `0`  | PASS — claim survived falsification attempt                            |
| `10` | FAIL — claim was falsified, or `guard` scan found a FAIL/STALE claim   |
| `11` | Guard violation — text guard matched a non-PASS claim                  |
| `2`  | Bad spec — malformed, placeholders present, or verdict INCONCLUSIVE    |
| `3`  | Hash mismatch — the spec drifted after lock (use `lock --force`)       |

`INCONCLUSIVE` is a run-level outcome rolled into exit `2`: it fires when
`metric_fn` returns `(value, n)` and `n < minimum_sample_size`. A
persistent `verdict.json` with `verdict: INCONCLUSIVE` is written so
`guard` can see the state across invocations.

## Validation

Claim specs are validated against [`hypothesis.schema.yaml`](hypothesis.schema.yaml)
before they can be locked or run.

**Required fields** (exit `2` if missing or the wrong type):

- `claim` — a string
- `falsification.failure_criteria` — at least one `{metric, direction, threshold}` entry
- `falsification.minimum_sample_size` — positive integer
- `falsification.stopping_rule` — string
- `experiment.command` — string
- `experiment.metric_fn` — string in `module:function` form

`environment` and `artifacts` are optional. `experiment.dataset` is
optional but recommended.

**Placeholder guard.** `falsify lock` refuses to lock a spec whose string
fields still contain placeholder markers: `<...>`, `TODO`, `FIXME`,
`REPLACE_ME`, `XXX`. This prevents the `examples/template.yaml` scaffold
from being locked by accident. The CLI exits `2` (bad spec) until the
placeholders are replaced with real values.

## Git hook (commit-msg guard)

Block commits whose message affirmatively references a hypothesis that
has not actually passed. `hooks/commit-msg` invokes
`falsify guard "$commit_message"`; if the message contains an
affirmative keyword (*confirmed*, *proven*, *validated*, *works*,
*successful*) and fuzzy-matches a claim whose latest verdict is FAIL or
INCONCLUSIVE, the commit is rejected with exit 11.

Install as a symlink (preferred — updates flow through automatically):

```bash
ln -sf "$(pwd)/hooks/commit-msg" .git/hooks/commit-msg
```

Or copy it, for environments without symlinks:

```bash
cp hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

## Layout

```
falsify.py           single-file CLI
examples/            example claims
tests/               test suite
hooks/               git / CI hook templates
.claude/skills/      Claude Code skills for authoring claims
.claude/agents/      Claude Code agents for review and verdict
```

## Status

Hackathon project. Interfaces may change.

## License

MIT — see [LICENSE](LICENSE).
