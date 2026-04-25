# CLAUDE.md — instructions for Claude Code in this repo

## Project one-liner

Falsification Engine is a stdlib-only CLI that enforces
pre-registration of empirical claims: you lock a spec with a
SHA-256 canonical-YAML hash before running an experiment. The
invariant it enforces is simple — the claim cannot change after
the data is seen, because any edit breaks the hash.

## Prime Directive

> Every claim is locked BEFORE it is run.
>
> Hash mismatches are never silenced.
>
> Threshold edits require an explicit relock and a visible audit
> entry.

Every rule below exists to protect this directive. When in doubt,
choose the option that makes dishonesty more visible, not less.

## File layout

- `falsify.py` — single-file CLI, 18 subcommands, stdlib + pyyaml.
- `hypothesis.schema.yaml` — spec schema + placeholder-marker list.
- `mcp_server/` — optional Model Context Protocol server exposing
  the verdict store to Claude Desktop / Claude Code.
- `.claude/skills/` — five in-session Claude skills (see below).
- `.claude/agents/` — two forked-context subagents.
- `managed_agents/` — Anthropic Console deployment manifests.
- `claims/` — user-facing claim sources (spec + metric + data)
  when using `init --template`.
- `examples/` — committed fixtures: `juju_sample/`, `hello_claim/`.
- `docs/` — `ARCHITECTURE.md`, `ADVERSARIAL.md`, `EXAMPLES.md`,
  `PR_REVIEW.md`, `DEMO_SHOT_LIST.md`, and more.
- `tests/` — stdlib `unittest` suite plus `smoke_test.sh`.
- `hooks/` — the `commit-msg` guard.
- `.github/workflows/` — CI + release pipelines.

## Available Claude skills

- **`hypothesis-author`** — interactive five-question dialogue
  that drafts a falsifiable `spec.yaml`. **Use when:** a user
  describes an empirical claim in prose and there is no spec yet.
- **`falsify`** — orchestrator that routes any empirical claim
  through `lock → run → verdict`. **Use when:** the user has a
  claim in mind and wants the machinery to run end-to-end.
- **`claim-audit`** — lightweight keyword+regex audit against the
  verdict log, with escalation to the `claim-auditor` subagent.
  **Use when:** the user pastes text (commit message, release
  note, README line) and asks "does this match what we've
  actually measured?"
- **`claim-review`** — PR-diff honesty reviewer. Flags unlocked
  specs, silent threshold edits, and broken `metric_fn` targets.
  **Use when:** reviewing a pull request that touches `claims/`,
  `examples/**/spec.yaml`, or any metric module.
- **`falsify-ci-doctor`** — one-shot CI failure triage. Ingests
  `make release-check` output, identifies which of the 12 gates
  failed, and maps each failure to an exact fix command. **Use
  when:** release-check exits 1 or CI is red and the cause is
  not obvious from the first line of output.

## Available subagents

- **`claim-auditor`** — forked-context semantic reviewer. Loads
  the full verdict store plus the input text and cross-references
  with paraphrase awareness. Meant for nightly jobs or heavy PR
  reviews.
- **`verdict-refresher`** — forked-context autonomous maintainer.
  Reads `falsify stats --json`, re-runs stale specs via the CLI,
  and posts a markdown summary. Scheduled, not per-PR.

## Available slash commands

- **`/new-claim <template> [name]`** — guided flow that scaffolds
  a claim from one of five templates, opens the spec for review,
  locks, runs, and reports the verdict. Escalates to `falsify
  why` on FAIL. **Use when:** onboarding a new claim end-to-end.
- **`/audit-claims`** — repo-wide semantic audit. Combines
  `falsify list/stats/score` with the `claim-audit` skill's
  findings into a single severity-ranked markdown report. **Use
  when:** pre-release, PR review of claim changes, or a quarterly
  honesty check.
- **`/ship-verdict <name>`** — four-gate release-readiness check
  (verdict PASS, state not STALE, `falsify replay` reproducible,
  `falsify verify --strict` chain intact). Does not ship anything
  itself; it is the pre-ship verification gate. **Use when:** the
  last check before tagging a release or merging a
  production-critical claim change.

## Development rules

1. **stdlib + pyyaml only.** No new runtime dependencies without
   ADR-level discussion and agreement.
2. **All tests must pass before any commit.** Run `make ci`.
3. **Exit codes are API.** `0` PASS, `10` FAIL, `2` bad spec,
   `3` hash mismatch, `11` guard violation. Do not change
   semantics without a major version bump.
4. **Canonical YAML uses `yaml.safe_dump(..., sort_keys=True,
   default_flow_style=False)`.** Do not change this serialization
   without a documented migration path.
5. **Spec hash is SHA-256 over canonical YAML bytes.** Do not
   change the hash function without a major version and a forced
   re-lock migration.
6. **New subcommands require:** implementation + unittest +
   README mention + CHANGELOG entry + `docs/ARCHITECTURE.md`
   commands-table row. Omit any of those and the PR is incomplete.
7. **No emoji** in source, docs, tests, or CLI output. Plain
   text carries.
8. **Four-space indentation for Python; two-space for YAML;
   tabs only in `Makefile`.** The `.editorconfig` enforces this.

## When you (Claude) work on this repo

- Read `docs/ARCHITECTURE.md` before touching `falsify.py` — it
  is the source of truth for invariants and module responsibility.
- Read `docs/ADVERSARIAL.md` before adjusting any hash, lock, or
  canonical-YAML code — those are the attack surfaces the tool
  actively defends.
- Run `make ci && ./tests/smoke_test.sh` before proposing a
  commit. If either fails, fix forward before replying "done".
- Prefer extending an existing helper (`_derive_claim_state`,
  `_gather_stats_rows`, `_canonicalize`, `_load_metric_fn`,
  `_ago`, `_iter_claim_dirs`) over duplicating logic. Duplicate
  logic drifts; shared helpers keep the Prime Directive honest.
- Self-dogfooding matters. If you add a feature that has a
  measurable claim attached (latency, accuracy, coverage),
  also add the corresponding `falsify`-managed claim under
  `.falsify/self/` if it is meaningful.

## Self-dogfooding note

This repo uses falsify on itself — `.falsify/` is tracked in git
(only `runs/` subdirectories are ignored via `.gitignore`), so
the lock, spec, and latest verdict for every self-claim are
version-controlled alongside the code that produces them. Three
self-claims ship today, source in `claims/self/` and locks in
`.falsify/`:

- `cli_startup` — `python3 falsify.py --help` median over 5
  spawns must be below 500ms.
- `test_coverage_count` — the `tests/` directory must contain
  more than 400 `test_*` methods.
- `claude_surface` — `.claude/skills/`, `.claude/agents/`, and
  `.claude/commands/` must collectively hold more than 8
  artifacts.

`make dogfood` re-runs all three; CI runs it on every push.

## Out of scope

See `ROADMAP.md` for the full list of planned work. Out of scope
for 0.1.x:

- Bayesian / sequential stopping rules — tracked for 0.3.0.
- Plugin architecture for custom hashers — not planned; the SHA-256
  invariant is load-bearing.
- GUI — not planned; exit codes and JSON output are the interface.

## Release ritual

See `CONTRIBUTING.md` "Releasing (maintainer notes)" for the full
recipe. In short:

1. Bump `__version__` in `falsify.py` and `version` in
   `pyproject.toml` — `tests/test_pyproject.py` enforces parity.
2. Move items out of `CHANGELOG.md` `[Unreleased]` into a new
   dated `## [X.Y.Z] — YYYY-MM-DD` section.
3. Commit, then `git tag vX.Y.Z && git push --tags`.
4. `.github/workflows/release.yml` runs the tag-gated build +
   CHANGELOG extraction + GitHub Release creation.
5. Verify the Release page; fix forward if the workflow failed.

## Questions?

- Users looking for a hands-on walkthrough: `TUTORIAL.md`.
- Contributors: `CONTRIBUTING.md`.
- Auditors, security-minded reviewers, and skeptics:
  `docs/ADVERSARIAL.md`.
- "Why not just X?" objections: `docs/FAQ.md`.
- Feature matrix vs adjacent tools: `docs/COMPARISON.md`.
- Term definitions cross-referenced across the docs:
  `docs/GLOSSARY.md`.
- Concrete adoption scenarios — how an ML team, a DevOps team,
  and a research group would actually use falsify this week:
  `docs/CASE_STUDIES.md`.
