# Falsification Engine

> Pre-registration and CI for AI-agent claims. Lock the hypothesis
> before the data. Get a deterministic PASS or FAIL — not a story.

<!-- ![CI](https://github.com/<user>/<repo>/actions/workflows/falsify.yml/badge.svg) ![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg) -->

**Current version: 0.1.0** — run `python3 falsify.py --version`.

## Why

AI agents make empirical claims all day — *"accuracy is up"*, *"the
new retriever is faster"*, *"this filter catches every edge case"*.
We rarely pin down the threshold, the metric, or the stopping rule
before the data arrives.

Without pre-registration, every verdict is post-hoc rationalization:
the goalposts move a little, the sample is chosen a little, the
winning explanation is kept.

Falsification Engine forces scientific discipline onto that loop.
You declare the test, lock the spec with a cryptographic hash, run
the experiment, and read the exit code. PASS or FAIL is mechanical,
not rhetorical — and CI enforces it on every push.

## What you get

- A single-file CLI (`falsify`) with **11 subcommands**: `init`,
  `lock`, `run`, `verdict`, `guard`, `list`, `stats`, `diff`, `hook`,
  `doctor`, `version`.
- A `commit-msg` git hook that blocks commits whose messages
  contradict a locked verdict.
- A GitHub Actions workflow that re-verdicts every push and PR
  across Python 3.11 and 3.12.
- **Three Claude Code skills** and **two forked-context subagents**
  that draft specs, audit arbitrary text against the verdict log,
  and keep the log itself fresh.

## Install

```bash
pip install -e .
```

After install, `falsify` is available as a command on your `PATH`
— no `python3 falsify.py` prefix needed. The `-e` editable form is
handy during development; drop the flag for a regular install.

## Quickstart

```bash
./demo.sh   # auto-narrated: PASS → tamper → FAIL → guard block

# Either form works — `falsify` is the installed entry point,
# `python3 falsify.py` is the uninstalled fallback.
falsify init my_claim
# edit .falsify/my_claim/spec.yaml to fill in the template
falsify lock my_claim
falsify run my_claim
falsify verdict my_claim
falsify hook install      # enable the commit-msg guard
```

Exit code `0` on PASS, `10` on FAIL. Everything else is documented
below.

### Developer commands

```bash
make install   # pip install pyyaml
make test      # run unittest suite
make smoke     # run tests/smoke_test.sh
make demo      # JUJU end-to-end (lock → run → verdict)
```

See [Makefile](Makefile) for all targets (`make help`).

## Exit codes

| Code | Meaning                                       |
|------|-----------------------------------------------|
| 0    | PASS                                          |
| 10   | FAIL                                          |
| 2    | Bad spec / INCONCLUSIVE                       |
| 3    | Hash mismatch (spec tampered)                 |
| 11   | Guard violation (commit blocked)              |

## The Opus 4.7 layers

**Skills** (`.claude/skills/`) — in-session helpers that fire on
trigger phrases.
- `hypothesis-author` walks the user through a 5-question dialogue
  and writes a falsifiable `spec.yaml`.
- `falsify` is the orchestrator: routes any empirical claim to the
  right place in the init → lock → run → verdict pipeline.
- `claim-audit` runs a fast keyword+regex audit over pasted text
  and escalates to the `claim-auditor` subagent when paraphrases or
  >2 claims show up.

**Subagents** (`.claude/agents/`) — forked-context agents invoked
via the `Task` tool for heavier work.
- `claim-auditor` does the semantic cross-reference that the
  keyword-pass `claim-audit` skill deliberately skips; used on PR
  bodies, release notes, and README edits.
- `verdict-refresher` scans `.falsify/*/` for STALE, INCONCLUSIVE,
  or UNRUN verdicts and re-runs them through the CLI — keeping
  `guard` decisions trustworthy.

**CI** (`.github/workflows/falsify.yml`) — on every push and PR,
the workflow runs the unittest suite, `tests/smoke_test.sh`, the
JUJU end-to-end (`lock` → `run` → `verdict`), a guard self-check,
and a skill-lint pass over every SKILL.md and agent file.

## Demo

- Walk through the pipeline in 5 runnable steps: [DEMO.md](DEMO.md).
- Second-by-second shooting script for the 3-minute video:
  [docs/DEMO_SHOT_LIST.md](docs/DEMO_SHOT_LIST.md).
- Four more claim types (accuracy regression, latency gate,
  prediction calibration, LLM agreement, AB test):
  [docs/EXAMPLES.md](docs/EXAMPLES.md).

## Install the git hook

```bash
cp hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Or, as a symlink so hook updates propagate automatically:

```bash
ln -sf "$(pwd)/hooks/commit-msg" .git/hooks/commit-msg
```

## Repository layout

- `falsify.py` — single-file CLI, stdlib + pyyaml only.
- `hypothesis.schema.yaml` — spec schema (claim, falsification,
  experiment, environment, artifacts).
- `examples/hello_claim/` — tiny smoke-test fixture.
- `examples/juju_sample/` — anonymized 20-row prediction ledger
  for the Brier score demo.
- `hooks/commit-msg` — the guard hook.
- `tests/` — `unittest` suite plus `smoke_test.sh` end-to-end driver.
- `.claude/skills/` — the three in-session skills.
- `.claude/agents/` — the two forked-context subagents.
- `.github/workflows/` — CI.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the post-hackathon direction.

## License

MIT. See [LICENSE](LICENSE).

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

## Built with

Claude Opus 4.7 (1M context), in five days, for the Anthropic
Built with Opus 4.7 hackathon.
