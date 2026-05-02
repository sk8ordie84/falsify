# Changelog

All notable changes to Falsification Engine are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); version
numbers follow [Semantic Versioning](https://semver.org).

## [Unreleased]

## [0.1.3] — 2026-05-02

Documentation, brand, and metadata refresh. No functional code changes.

### Changed

- **Repository transferred** from `github.com/sk8ordie84/falsify` to `github.com/studio-11-co/falsify`. Old URLs 301-redirect to canonical; all in-source references (README, spec, test vectors, preprint .tex, Dockerfile, CITATION.cff, action workflows, package metadata) updated to the new canonical URL.
- **Editor identity standardised** from `Studio-11` (hyphenated) to `Studio 11` (no hyphen) across spec, CHANGELOG, CITATION, generator footers, and live spec.falsify.dev hosting. Aligns with falsify.dev landing and commercial paperwork.
- **Pre-commit hook reference** in README updated to `rev: v0.1.3`.

### Why this release

PyPI metadata (`Repository`, `Issues`, `Changelog` URLs in `pyproject.toml`) was frozen at v0.1.2 with the previous GitHub URL. This release refreshes metadata so `pip show falsify` and PyPI's project page reflect the canonical org. No code changes; behaviour identical to 0.1.2.

## [0.1.2] — 2026-05-01

The PRML specification day — three reference implementations across Python, JavaScript, and Go all reproducing the v0.1 conformance vectors byte-for-byte; six additional v0.2 candidate vectors; four cross-language portability findings documented; arXiv preprint, compliance landing copy, positioning matrix, v0.2 RFC roadmap, and the HumanEval worked example all published. Code itself unchanged from 0.1.1; this release exists to mark a specification-level milestone.

### Added — specification

- **PRML v0.1 specification** at `spec.falsify.dev/v0.1` (RFC-style, CC BY 4.0, ~18 pages). Editor: Studio 11 (Independent).
- **Twelve v0.1 conformance test vectors** with locked SHA-256 digests under `spec/test-vectors/v0.1/`.
- **Six v0.2 candidate vectors** (TV-013 through TV-018) under `spec/v0.2/test-vectors-candidates.json`. Five pass byte-for-byte across all three reference implementations; TV-018 surfaces Finding 4 (small-magnitude float rendering diverges three ways across language stdlibs).
- **arXiv preprint** in `spec/paper/prml-v0.1-preprint.tex` — 14-page LaTeX working draft, CC BY 4.0, cs.CR submission in flight.
- **EU AI Act mapping** in `spec/compliance/AI-Act-mapping-v0.1.md` — Articles 12, 17, 18, 50, 72, 73 with field-level bindings.
- **Compliance landing copy** in `spec/compliance/landing.md` — for compliance leads, AI governance officers, notified body assessors.
- **Positioning matrix** in `spec/analysis/positioning-v0.1.md` — PRML vs in-toto, SLSA, Model Cards, HELM, ClinicalTrials.gov; two-axis framework; six common confusions cleared.
- **Canonicalization portability findings** in `spec/analysis/canonicalization-portability-v0.1.md` — four cross-language gotchas surfaced by the JS and Go implementations, with severity asymmetry analysis per language.
- **v0.2 RFC roadmap** in `spec/v0.2/ROADMAP.md` — ten changes, five open RFC questions, freeze targeted 2026-05-22, release 2026-06-15.
- **PRML scoring methodology** in `spec/analysis/scoring-methodology-v0.1.md` (carried over from 0.1.1 publishing window) with twelve worked examples.

### Added — implementations

- **`impl/js/falsify.js`** — Node.js second reference implementation. ~400 LOC, hand-rolled canonicalizer, zero runtime dependencies beyond Node.js stdlib. Reproduces all twelve v0.1 vectors byte-for-byte. CLI: `init / lock / verify / hash / test-vectors`.
- **`impl/go/falsify.go`** — Go third reference implementation. ~450 LOC, hand-rolled canonicalizer, standard library only. Reproduces all twelve v0.1 vectors byte-for-byte on first compile. Notably, Go's `encoding/json` with `Decoder.UseNumber()` handles two of the three v0.1 portability findings without workarounds.
- **`impl/js/README.md`** and **`impl/go/README.md`** — build / run docs and severity-asymmetry tables.

### Added — tests

- `tests/test_prml_v02_candidates.py` — 17 new unittests asserting that the Python reference reproduces the v0.2 candidate vectors. Total test count: 547 → 564, no regressions.

### Added — examples

- `examples/humaneval-walkthrough/` — end-to-end procedure document and runnable Python script demonstrating PRML on a real benchmark (HumanEval `pass@1`). Covers pinning the dataset, locking the manifest, running inference, verifying, and tamper detection.

### Added — operational artefacts (private to the launch directory)

- `proposals/_TEMPLATES.md` — six proposal / SOW / MSA / invoice templates for the post-outreach sales flow.
- `outreach/eu-ai-act-compliance-targets.md` — twelve named EU AI Act compliance / consulting / provider / academic targets with custom cold-mail angles.
- `outreach/MONDAY-2026-05-04-batch.md` — twelve fully personalised outreach mails ready to fire Monday 2026-05-04 at 09:00–11:00 CET.
- `monitoring/baseline-2026-05-01.md` — engagement baseline snapshot.
- `monitoring/sunday-monday-tuesday-playbook.md` — hour-by-hour operational playbook for Sunday, Monday, and Tuesday.
- `landing/falsify-dev-content-brief.md` — content brief for upgrading the falsify.dev landing page.
- `blog/i-implemented-prml-in-two-languages.md` — dev.to-format blog post covering Findings 1–3 (publishable from Sunday onward).

### Changed

- `README.md` — new "Specification artifacts" section surfacing the eight new public docs and three reference implementations; "Repository layout" updated with `impl/`, `spec/analysis/`, `spec/compliance/`, `spec/paper/`, `spec/v0.2/`; "Roadmap" section expanded to point at both the CLI roadmap (`ROADMAP.md`) and the spec roadmap (`spec/v0.2/ROADMAP.md`).
- `ROADMAP.md` — rewritten to clearly separate CLI tool features from PRML specification evolution. CLI v0.2 retargeted to 2026-06-15, three weeks after the spec freeze on 2026-05-22.
- `spec/index.html` — new "Related documents" section linking the eight new public artefacts via canonical GitHub blob URLs.

### Notes

- Code unchanged from 0.1.1: same canonicalizer, same exit codes, same 547 + 17 = 564 tests passing. This release marks the specification milestone, not a code change.
- The Finding 4 cross-language float divergence (TV-018) is documented but deliberately not patched in v0.1; the v0.2 grammar (RFC-Q-04, always-quote-numbers) is the strategic fix.
- arXiv submission to cs.CR is in flight pending endorsement from a TUF / in-toto / SLSA contributor.

## [0.1.1] — 2026-04-28

First public release on PyPI. `pip install falsify` now works.

### Added

- PyPI publication: `pip install falsify` installs the CLI globally.
- `Homepage = "https://falsify.dev"` URL in `pyproject.toml`.

### Changed

- All public-facing references migrated from intermediate brand
  surfaces to the project's own surfaces (landing page, repo
  metadata).

### Notes

- Code unchanged from 0.1.0 — same 518 tests, same canonical
  YAML hashing, same exit-code contract. This release exists
  to make the CLI installable for non-developers.

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

- `falsify bench` — micro-benchmark CLI command latency with
  min / median / p95 / max / mean / stddev per command; text and
  `--json` outputs; configurable `--runs` and `--warmup`.
- `docs/CASE_STUDIES.md` — three concrete adoption scenarios
  (ML team, DevOps team, research group) with literal command
  sequences.
- `docs/GLOSSARY.md` — 30+ term glossary with cross-references
  across all docs.
- 5th Claude skill `falsify-ci-doctor` — one-shot CI failure
  triage mapping `release-check` FAIL gates to exact fix
  commands.
- `.gitignore` rules for run artifacts
  (`.falsify/*/latest_run`, `verdict.json`, `runs/`);
  `.github/CODEOWNERS`, `FUNDING.yml`, `dependabot.yml` for
  GitHub repo maturity.
- `tests/test_integration_e2e.py` — single end-to-end lifecycle
  test with 18 stages covering init, lock, run, verdict, stats,
  trend, why, score, export, verify, replay, tampering detection,
  honest relock, and stale detection.
- `scripts/release_check.py` and `make release-check` — 12-gate
  pre-release validator covering version consistency, CHANGELOG,
  placeholders, tests, smoke, dogfood, docs, Claude surface,
  installability, git cleanliness, and self-integrity.
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

[Unreleased]: https://github.com/studio-11-co/falsify/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/studio-11-co/falsify/releases/tag/v0.1.2
[0.1.1]: https://github.com/studio-11-co/falsify/releases/tag/v0.1.1
[0.1.0]: https://github.com/studio-11-co/falsify/releases/tag/v0.1.0
