# Roadmap

This roadmap is directional, not a commitment. Items move as the
community uses the tool and finds out what actually matters.

## Now — shipped in 0.1.0 (April 21, 2026)

See [CHANGELOG.md](CHANGELOG.md) for the full list. Highlights:

- Core CLI: `init`, `lock`, `run`, `verdict`, `guard`, `list`,
  `stats`, `diff`, `hook`, `doctor`, `version`.
- Canonical YAML + SHA-256 hashing.
- Commit-msg guard hook with `falsify hook install` auto-setup.
- CI workflow with the JUJU end-to-end gate on every push / PR.
- Three Claude Code skills and two forked-context subagents.
- `DEMO.md`, `docs/ARCHITECTURE.md`, `docs/EXAMPLES.md`.
- MIT licensed, installable via `pip install .`.

## Next — 0.2.0 target (May 2026)

Concrete additions planned for the first post-hackathon release:

- **MCP verdict-log server**: expose `.falsify/*/verdict.json` via
  Model Context Protocol so any Claude session — Desktop, Code,
  custom — can query locked verdicts without shelling out.
- **Managed Agents integration**: deploy `verdict-refresher` on a
  cron schedule, posting refresh summaries to a repo Discussion or
  Issue thread.
- **GitHub PR bot**: a `falsify audit` mode that comments on PRs
  with the `claim-audit` result inline.
- **Multi-metric specs**: one spec can assert
  `accuracy ≥ 0.92 AND p95_latency ≤ 200ms`. Verdict is
  AND-composed across every `failure_criteria` entry.
- **Remote artifacts**: optional S3 / GCS backend for
  `.falsify/<name>/runs/` so teams can share verdict history
  without committing run artifacts to git.

## Soon — 0.3.0 target (Q3 2026)

Larger moves, scoped loosely:

- **Spec library**: a curated set of shareable spec templates
  (`falsify install-template classification-accuracy-v1`) with
  versioned schemas.
- **Bayesian stopping rules**: first-class support for sequential
  / adaptive stopping, not just fixed sample. The spec declares
  the rule; falsify enforces it and rejects mid-run peeking.
- **Diff-aware reruns**: `falsify run <name> --only-if-changed`
  detects which inputs changed since the last run and skips
  redundant work.
- **Provenance chaining**: link each verdict to the git SHA plus
  dataset hash so a third party can reproduce the PASS/FAIL.

## Later — speculative

Ideas worth exploring if the tool sees adoption:

- **VS Code / JetBrains extension**: inline verdict status in
  editor gutters.
- **Slack / Discord bot**: post verdict changes to a channel;
  challenge-mode mini-games.
- **Anti-p-hacking gamification**: personal / team leaderboards
  for pre-registration discipline.
- **Federated verdict registry**: cross-org claim registry,
  opt-in and privacy-preserving.
- **AI agent integration**: agents auto-generate specs from a
  plain-English claim via the `hypothesis-author` skill, commit
  them, and run `falsify lock` before acting on the claim.

## What won't ship (non-goals)

Honest scope boundaries:

- **Not a statistics package.** We don't compute p-values or
  confidence intervals. The spec declares the threshold; the tool
  enforces it.
- **Not an experiment orchestrator.** `falsify` runs one command
  per spec and reads the output. Airflow / Dagster / Prefect do
  that job better.
- **Not a secrets manager.** Specs must not embed API keys; pass
  them through environment variables read by
  `experiment.command`.
- **Not a distributed system.** The verdict store is per-repo and
  on-disk. Remote backends (0.2.x) are opt-in sync, not a
  replacement.

## How to influence this roadmap

- Open a GitHub issue with the `roadmap` label describing the use
  case you need.
- If you want to contribute a 0.2.0 feature, start with
  [CONTRIBUTING.md](CONTRIBUTING.md).
- For private or commercial inquiries, contact the maintainer
  directly (email in [`.github/SECURITY.md`](.github/SECURITY.md)).

## A note on discipline

Every item above is subject to the same contract as 0.1.0:
deterministic exit codes, canonical hashing, stdlib + `pyyaml`
dependencies unless a compelling case exists. Feature creep dilutes
the trust the tool sells. Small, deterministic, verifiable — that's
the product.
