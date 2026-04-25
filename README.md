<img src="brand/lockup.svg" alt="falsify" width="320">

> **Pre-registration + CI for AI-agent claims.** Lock the claim and threshold with SHA-256 *before* running the experiment — or the result doesn't count.

![CI](https://github.com/sk8ordie84/falsify/actions/workflows/falsify.yml/badge.svg)
![coverage](https://img.shields.io/badge/tests-518%20passing-brightgreen)
![honesty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/sk8ordie84/falsify/main/.falsify/badge.json)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-MIT-blue.svg)

> Code: MIT. "FALSIFY" name and chevron logo: ™ reserved. See [NOTICE](NOTICE) · [docs/COMMERCIAL.md](docs/COMMERCIAL.md).

---

## The problem

Your team claims the model hits **94% accuracy**. You ship it. Three weeks later a customer proves the real number is **71%**.

The claim was never *falsifiable*. Nobody wrote down — cryptographically, before the experiment ran — what "94%" meant, which dataset, which metric, which threshold. So when the number changed, nobody could say whether the claim was wrong, the data drifted, or the metric got silently relaxed.

**Falsify fixes this with a single idea from science:** you must pre-register the claim *before* you run the experiment. If you change the spec after seeing the data, the hash changes, the audit trail breaks, and CI fails with exit code 3.

    $ falsify lock accuracy_claim        # SHA-256 the spec
    $ falsify run  accuracy_claim        # reproducible experiment
    $ falsify verdict accuracy_claim     # exit 0 = PASS, 10 = FAIL, 3 = tampered

Deterministic exit codes are the API. CI gates on them. Humans read the audit trail. The claim either survives contact with the data or it doesn't.

---

## 90-second demo

[**▶ Watch the 90-second demo on YouTube**](https://youtu.be/vVZTNeak5PA)

Lock a claim, run it, watch it PASS. Then tamper with the threshold and watch CI refuse to run. Full storyboard in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

---

## Why this matters

Every week another paper, blog post, or product launch claims an AI metric that quietly evaporates under scrutiny. It's not usually malice — it's that the claim was never structured to be falsifiable. Falsify is the smallest possible tool that forces that structure.

- **ML teams** — gate deploys on pre-registered accuracy / NDCG / recall
- **DevOps** — treat p95 latency claims the same way you treat tests
- **LLM pipelines** — pin prompt + eval + threshold so "it works" means something
- **Research** — replicate a paper by running its spec.lock.json

See [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) for three concrete adoption stories.

---

**Current version:** 0.1.0 — run `python3 falsify.py --version`.
**Working with Claude Code?** See [CLAUDE.md](CLAUDE.md).

---

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

- A single-file CLI (`falsify`) with **16 subcommands**: `init`,
  `lock`, `run`, `verdict`, `guard`, `list`, `stats`, `diff`, `hook`,
  `doctor`, `version`, `export`, `verify`, `replay`, `why`, `trend`.
- A `commit-msg` git hook that blocks commits whose messages
  contradict a locked verdict.
- A GitHub Actions workflow that re-verdicts every push and PR
  across Python 3.11 and 3.12.
- **Five Claude Code skills** and **two forked-context subagents**
  that draft specs, audit arbitrary text against the verdict log,
  review PR diffs for honesty violations, and keep the log itself
  fresh.

## Install

```bash
pip install -e .
```

After install, `falsify` is available as a command on your `PATH`
— no `python3 falsify.py` prefix needed. The `-e` editable form is
handy during development; drop the flag for a regular install.

### Docker

```bash
docker build -t falsify-demo . && docker run --rm -it falsify-demo
```

Runs the auto-demo in a clean container. See
[docs/DOCKER.md](docs/DOCKER.md) for interactive and repo-mount
modes.

### pre-commit integration

Consume falsify's hooks from your own repo:

```yaml
repos:
  - repo: https://github.com/sk8ordie84/falsify
    rev: main  # pin a tag (e.g. v0.1.1) once releases start
    hooks:
      - id: falsify-guard
      - id: falsify-doctor
```

Then `pre-commit install && pre-commit install --hook-type commit-msg`.
See [docs/PRE_COMMIT.md](docs/PRE_COMMIT.md) for the full list of
exported hooks and how this repo eats its own dog food.

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

New to pre-registration? Walk through [TUTORIAL.md](TUTORIAL.md) — 15 minutes, zero to first locked claim.

### Start from a template

```bash
falsify init --template accuracy
falsify lock accuracy
falsify run accuracy
falsify verdict accuracy
```

Five templates ship with a runnable spec + metric + dataset:

- `accuracy` — classifier holdout accuracy ≥ 0.80
- `latency` — p95 request latency ≤ 200 ms
- `brier` — probabilistic calibration Brier ≤ 0.25
- `llm-judge` — LLM-judge agreement rate ≥ 0.75
- `ab` — A/B test absolute lift ≥ 0.05

Each scaffolds into `claims/<name>/` (sources) and mirrors
`spec.yaml` into `.falsify/<name>/` so the CLI runtime works
without further setup. Override the default name with `--name`
or the directory with `--dir`.

### Developer commands

```bash
make install   # pip install pyyaml
make test      # run unittest suite
make smoke     # run tests/smoke_test.sh
make demo      # JUJU end-to-end (lock → run → verdict)
```

See [Makefile](Makefile) for all targets (`make help`).

Questions and objections? See [docs/FAQ.md](docs/FAQ.md) — 15
direct answers to "why not just X?" questions.

Feature matrix vs adjacent tools: [docs/COMPARISON.md](docs/COMPARISON.md).

### Explain any claim

`falsify why <name>` is the human-friendly companion to `verdict`
— it always exits `0` and tells you exactly what the next honest
move is:

```
claim: juju
state: STALE
reasoning: the spec has been edited (sha256:1038219d75a8) but no run
  exists against this hash. Last run was against sha256:164f619d4860.
locked: yes (sha256:164f619d4860, 2h ago)
last run: 2026-04-22T02:10:17+00:00 (2h ago)
next action: `falsify run <name>` to produce a fresh verdict against
  the current spec.
```

Add `--json` for a scripted pipeline, `--verbose` for full hashes
and the last five runs.

### Spot drift with a sparkline

`falsify trend <name>` draws an ASCII sparkline of the metric
across its recorded runs, marks the threshold line, and classifies
the trajectory as **improving**, **degrading**, **flat**, or
**mixed**.

```
claim: juju
threshold: 0.25 (direction: below)
runs: 20 shown (of 20)

▁▂▂▃▃▄▄▅▅▆▆▆▇▇████
                    TT
threshold=0.25 (shown)

first: 0.12 @ ... (PASS)
last:  0.23 @ ... (PASS)
min:   0.09
max:   0.23
mean:  0.17
latest verdict: PASS
trend: degrading
```

`--ascii` swaps in `_.oO#`; `--width` resizes the sparkline;
`--last` caps history (default 20, max 200).

### Measure the CLI itself

`falsify bench` spawns each subcommand under a fresh temporary
directory and records per-command latency (min / median / p95 /
max / mean / stddev). Useful as a sanity check before a release
or when investigating a suspected startup-time regression.

```bash
falsify bench --runs 5 --commands "--help,list,stats,score"
falsify bench --runs 5 --json     # machine-readable output
```

`--runs <N>` sets the timed-iteration count (default 5, capped at
100); `--warmup <N>` discards the first N spawns so JIT / import
caches stabilize before timing (default 1).

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
- `claim-review` reads a PR diff and flags unlocked specs, silent
  threshold edits, and `metric_fn` references to missing modules —
  runs in PR CI, exits `1` on any CRITICAL finding. See
  [`docs/PR_REVIEW.md`](docs/PR_REVIEW.md).
- `falsify-ci-doctor` ingests `make release-check` output and
  maps each FAIL gate to a likely cause and an exact fix command
  — one-shot triage when CI is red.

**Subagents** (`.claude/agents/`) — forked-context agents invoked
via the `Task` tool for heavier work.
- `claim-auditor` does the semantic cross-reference that the
  keyword-pass `claim-audit` skill deliberately skips; used on PR
  bodies, release notes, and README edits.
- `verdict-refresher` scans `.falsify/*/` for STALE, INCONCLUSIVE,
  or UNRUN verdicts and re-runs them through the CLI — keeping
  `guard` decisions trustworthy.

**Slash commands** (`.claude/commands/`) — in-IDE shortcuts that
compose the skills and CLI.
- `/new-claim <template> [name]` — guided scaffold → lock → run →
  verdict for one of the five templates.
- `/audit-claims` — repo-wide semantic audit; merges
  `list`/`stats`/`score` with findings from the `claim-audit`
  skill into a single markdown report.
- `/ship-verdict <name>` — four-gate release check (verdict,
  freshness, replay, audit-chain). Exits non-zero on any gate
  failure. Does not ship; only verifies.

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

## MCP integration

Expose the verdict store to Claude Desktop / Claude Code via
Model Context Protocol with four read-only tools (`list_verdicts`,
`get_verdict`, `get_stats`, `check_claim`) and three resource URIs.

```bash
pip install -e '.[mcp]'
python -m mcp_server   # speaks MCP over stdio
```

Then merge the snippet in
[`mcp_server/claude_desktop_config.example.json`](mcp_server/claude_desktop_config.example.json)
into your Claude Desktop config, pointing `cwd` at your local
clone. Every Claude session in your org can now query live
verdicts — no more *"I think the latency claim still passes"*;
Claude just asks the MCP server. Falsify itself runs without the
SDK; if `mcp` isn't installed, `python -m mcp_server` exits 2 with
a clear install hint. Full surface in
[`mcp_server/README.md`](mcp_server/README.md).

### Managed Agents (optional)

Deploy the two subagents (`verdict-refresher`, `claim-auditor`)
to Anthropic Console for scheduled and on-demand execution.
See [docs/MANAGED_AGENTS.md](docs/MANAGED_AGENTS.md) for the
setup recipe and manifests under
[`managed_agents/`](managed_agents/).

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
- `.claude/skills/` — the five in-session skills.
- `.claude/agents/` — the two forked-context subagents.
- `.claude/commands/` — the three slash commands.
- `.github/workflows/` — CI.

## Self-dogfooding

Falsify uses itself. Three real claims about this codebase live
under `claims/self/`:

- `cli_startup` — CLI startup stays under 500ms median
- `test_coverage_count` — test suite has more than 400 test methods
- `claude_surface` — Claude integration ships more than 8 artifacts

Run `make dogfood` to re-verify. CI runs these on every PR.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the post-hackathon direction.

## Trust model

Falsify is a discipline tool, not a zero-trust system. For a full
enumeration of attacks defended and NOT defended, with the exact
exit code or command that catches each, see
[docs/ADVERSARIAL.md](docs/ADVERSARIAL.md). For private disclosure
of invariant breaks, see [.github/SECURITY.md](.github/SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.
See [.github/CODEOWNERS](.github/CODEOWNERS) for module-level
reviewers and [.github/dependabot.yml](.github/dependabot.yml) for
automated dependency updates.
See [docs/GLOSSARY.md](docs/GLOSSARY.md) for definitions of every
term used across the docs.
See [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) for three concrete
adoption scenarios: ML team, DevOps team, research group.

## Built with

Claude Opus 4.7 (1M context), in three days, for the Anthropic
Built with Opus 4.7 hackathon.
