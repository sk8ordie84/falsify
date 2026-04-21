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

| Command   | Purpose                                                         |
|-----------|-----------------------------------------------------------------|
| `init`    | Scaffold a new claim spec                                       |
| `lock`    | Hash and freeze a claim (pre-registration)                      |
| `run`     | Evaluate a locked claim against current state                   |
| `verdict` | Report PASS/FAIL for a claim                                    |
| `guard`   | CI wrapper — exits non-zero if any locked claim is falsified    |
| `list`    | List all claims in the current repo with their status           |

## Exit codes

| Code | Meaning                                                    |
|------|------------------------------------------------------------|
| `0`  | PASS — claim survived falsification attempt                |
| `10` | FAIL — claim was falsified                                 |
| `2`  | Bad spec — the claim file is malformed                     |
| `3`  | Hash mismatch — the locked claim was tampered with         |

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
