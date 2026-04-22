# Changelog

All notable changes to Falsification Engine are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); version
numbers follow [Semantic Versioning](https://semver.org).

## [Unreleased]

### Documentation

- `SUBMISSION.md` rewritten with current scope numbers, sharper
  pitch, money-shot walkthrough, and an explicit known-gaps
  section.
- `docs/DEMO_SCRIPT.md` — 90-second demo video storyboard with
  TTS-ready voiceover, shot-by-shot terminal commands, and SRT
  captions.
- Clarified that direction `above`/`below` are strictly
  greater/less (not `>=`/`<=`) in `hypothesis.schema.yaml`
  inline docs and `docs/ARCHITECTURE.md` Core invariants.

### Changed

- `mcp_server/` upgraded from stub to real MCP-SDK implementation.
  Four tools (`list_verdicts`, `get_verdict`, `get_stats`,
  `check_claim`) and three resource URIs (`falsify://verdicts`,
  `falsify://verdicts/<claim>`, `falsify://stats`) registered via
  the `mcp.server.Server` decorators. Lazy SDK import — module
  loads cleanly without `mcp`; `python -m mcp_server` exits 2 with
  a clear hint when the SDK is missing. Plain helpers stay
  importable as `from mcp_server import list_verdicts, ...`.
  Optional install bumped to `mcp>=1.0.0`.

### Added

- Self-dogfooding — three locked claims (`cli_startup`,
  `test_coverage_count`, `claude_surface`) verify falsify's own
  properties; `make dogfood` re-runs them; CI gates on them.
- `docs/COMPARISON.md` — 15-row feature matrix vs MLflow, W&B,
  DVC, OSF, pytest, pre-commit with honest positioning paragraphs.
- Three Claude Code slash commands: `/new-claim` (guided
  scaffold→lock→run), `/audit-claims` (repo-wide semantic audit),
  `/ship-verdict` (release-gate verification).
- `docs/FAQ.md` — 15 direct answers to common objections (git
  hooks, OSF, MLflow, DVC, pytest, and more).
- `CLAUDE.md` — project instructions for Claude Code users,
  encoding the prime directive, file layout, skills/subagents, and
  non-negotiable development rules.
- `pyproject.toml` — installable as `pip install .` with a
  `falsify` console entry point (`falsify:main`).
- `ROADMAP.md` — post-hackathon direction (0.2.0 MCP + Managed
  Agents, 0.3.0 Bayesian stopping, non-goals, discipline note).
- `mcp_server/` — Model Context Protocol server scaffold exposing
  the verdict store as read-only resources and four tool
  functions (`list_verdicts`, `get_verdict`, `get_stats`,
  `check_claim`). Optional install via `pip install -e '.[mcp]'`;
  tool logic is implemented, `stdio_server` SDK adapter is
  stubbed pending SDK version pin.
- `managed_agents/` — Anthropic Console deployment manifests for
  `verdict-refresher` (scheduled, 6-hour cron) and `claim-auditor`
  (on-demand webhook).
- `docs/MANAGED_AGENTS.md` — Console setup guide, cost
  expectations, rollback, security notes.
- `falsify stats --html` — self-contained HTML dashboard with
  dark-mode-aware inline CSS, per-spec cards with state-colored
  badges. `--output PATH` writes to a file. `--json` and `--html`
  are mutually exclusive.
- `falsify export` — deterministic JSONL audit trail of every
  lock, run, and verdict. Read-only. Records carry
  `schema_version: 1` and verdict records include a `locked_hash`
  that chains back to the originating lock. Flags: `--output`,
  `--name`, `--since`, `--include-runs`.
- `falsify verify` — integrity check for JSONL audit trails.
  Validates hash chain (verdict `locked_hash` ↔ lock
  `canonical_hash`), per-spec timestamp monotonicity, no record
  reordering, and schema version. Exit 0 VALID, 10 INVALID,
  2 bad input. Flags: `--strict`, `--json`.
- `.github/workflows/release.yml` — tag-triggered release pipeline.
  Runs tests + smoke, verifies the `v*.*.*` tag matches
  `falsify.__version__`, builds sdist + wheel, publishes a GitHub
  Release with the matching `CHANGELOG` section as the body.
- `.pre-commit-hooks.yaml` — hook manifest for consumer repos:
  `falsify-guard` (commit-msg stage), `falsify-doctor` (pre-commit
  stage), `falsify-stats` (informational).
- `.pre-commit-config.yaml` — local pre-commit configuration:
  standard hygiene hooks plus three local ones
  (`falsify-guard-local`, `falsify-doctor-local`, `unittest-fast`).
- `docs/PRE_COMMIT.md` — setup guide for both use cases.
- `TUTORIAL.md` — 15-minute hands-on walkthrough from init to
  first locked PASS/FAIL cycle.
- `falsify replay <run-id>` — deterministically re-runs a stored
  run's metric and verifies the value matches exactly (tolerance
  configurable via `--tolerance`). New exit code path: `10` on
  mismatch, `3` on stale spec. `cmd_verdict` now also writes
  `verdict.json` into the run dir as a per-run snapshot so
  replay can target arbitrary historical runs.
- `falsify score` — single-number honesty metric across all
  claims with text / json / shields.io / svg outputs. Powers
  README badges and CI gating; default exits `10` only on
  `fail` status, `--strict` also exits on `warn`.
- `falsify init --template {accuracy,latency,brier,llm-judge,ab}`
  — scaffolds a complete working claim (spec + metric + dataset
  + claim-local README) into `claims/<name>/` and mirrors
  `spec.yaml` into `.falsify/<name>/` so the canonical CLI flow
  works without further setup. Flags: `--name`, `--dir`,
  `--force`. Hyphenated template names default to a snake_case
  claim name so the metric module is importable.
- `falsify why <claim>` — human-readable state diagnostic with
  actionable next steps for every claim state (PASS / FAIL /
  INCONCLUSIVE / STALE / UNRUN / UNLOCKED / UNKNOWN). Always
  exits 0 — informational. Flags: `--json`, `--verbose`.
- `falsify trend <claim>` — ASCII sparkline of the metric across
  recorded runs, with threshold overlay and an
  `improving` / `degrading` / `flat` / `mixed` classifier based
  on first-third vs last-third means. Flags: `--last N` (cap 200),
  `--width`, `--ascii`, `--json`.
- `docs/ADVERSARIAL.md` — threat model enumerating 8 defended and
  6 undefended attack classes with mitigations. Linked from
  README, SECURITY, and SUBMISSION.
- Claude skill `claim-review` — reviews PR diffs for unlocked
  specs, silent threshold edits, and broken `metric_fn`
  references. Runs in PR CI, exits `1` on any CRITICAL finding.
  Paired with [`docs/PR_REVIEW.md`](docs/PR_REVIEW.md) for setup.
- `Dockerfile` + `.dockerignore` — reproducible demo environment
  (`docker run --rm -it falsify-demo` fires the auto-demo).
- `docs/DOCKER.md` — quick run, interactive session, repo-mount,
  image size + build-determinism notes.

### Notes

Next: MCP verdict-log server, Managed Agents integration for cloud
verdict refresh, multi-metric specs.

## [0.1.0] — 2026-04-21

### Added

- **Core CLI**: `init`, `lock`, `run`, `verdict`, `guard`, `list`
  subcommands with deterministic exit codes (`0` PASS, `10` FAIL,
  `2` bad spec / INCONCLUSIVE, `3` hash mismatch, `11` guard
  violation).
- **Canonical YAML + SHA-256** hashing for spec locks — the same
  logical claim always hashes identically across machines; any
  semantic edit invalidates the lock.
- **JUJU anonymized sample** (`examples/juju_sample/`) — a 20-row
  prediction ledger fixture with a Brier score metric, for the
  hackathon demo.
- **Additional CLI subcommands**: `stats` (aggregate dashboard
  across all locked verdicts), `diff` (unified canonical-YAML diff
  between the lock and the current spec), `hook install / uninstall`
  (commit-msg guard management with backup), `doctor` (environment +
  repo + per-spec self-diagnostic), `version` (version string, also
  exposed as `--version`).
- **Three Claude Code skills** in `.claude/skills/`:
  `hypothesis-author` (five-question dialogue that drafts a
  falsifiable spec), `falsify` (orchestrator routing empirical
  claims to the right pipeline step), `claim-audit` (lightweight
  text audit with handoff to the `claim-auditor` subagent).
- **Two forked-context subagents** in `.claude/agents/`:
  `claim-auditor` (paraphrase-aware semantic cross-reference of
  arbitrary text against the verdict log), `verdict-refresher`
  (autonomous refresh of STALE / INCONCLUSIVE / UNRUN verdicts).
- **GitHub Actions CI** (`.github/workflows/falsify.yml`) —
  unittest suite + `tests/smoke_test.sh` + JUJU end-to-end
  (`lock` → `run` → `verdict`) + guard self-check, plus a dedicated
  skill-lint job that validates every `SKILL.md` and agent file.
- **Documentation**: `README.md` (jury-facing front door),
  `DEMO.md` (five-step runnable walkthrough),
  `docs/DEMO_SHOT_LIST.md` (second-by-second video script),
  `docs/ARCHITECTURE.md` (one-page technical overview with data
  flow + invariants), `CONTRIBUTING.md` (ground rules, PR checklist,
  skill/agent recipes), `SUBMISSION.md` (hackathon submission
  draft).

### Notes

- Initial public release for the Anthropic Built with Opus 4.7
  hackathon (April 21–26, 2026).
- MIT licensed. New work — not derived from prior projects.
- Built with Claude Code + Opus 4.7 (1M context). Every commit
  carries a `Co-Authored-By:` trailer.

[Unreleased]: https://github.com/<USER>/falsify-hackathon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/<USER>/falsify-hackathon/releases/tag/v0.1.0
