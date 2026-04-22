---
name: falsify-ci-doctor
description: Diagnose a failing falsify CI run. Reads `make release-check` output, unittest failure tracebacks, and smoke/dogfood stderr. Identifies which of the 12 gates failed and why, cross-references likely causes (spec hash mismatch, stale verdict, missing dependency, regressed test), and suggests exact fix commands. Call this skill when release-check returns exit 1 or when CI is red and the cause is not obvious.
allowed-tools: Bash(git:*), Bash(python3:*), Bash(make:*), Read, Glob, Grep
context: fork
---

# falsify-ci-doctor

One-shot triage for a red falsify CI. Reads the structured output
of `make release-check`, isolates the failing gate(s), re-runs the
specific sub-command that caused the failure with verbose flags,
and emits a markdown report that pairs each failure with the exact
command to run next. This skill *diagnoses*; it does not patch.

## When to use

- After `make release-check` reports one or more FAIL gates and
  you need to understand which gate broke and why before touching
  code.
- When the CI workflow is red and you need a one-shot triage to
  decide whether the regression is in tests, in a spec, in docs,
  or in a placeholder scan.
- When a teammate reports "falsify is broken" and you need to
  quickly assess whether it is a real regression or an expected
  WARN (e.g., `<USER>` placeholders that disappear post-push).
- Before a release, as a sanity sweep before tagging — faster
  than reading 12 gate messages by hand.

## What this skill does

1. Runs `python3 scripts/release_check.py --all --json` and
   captures the full structured report (every gate, even after
   a FAIL, thanks to `--all`).
2. Walks the JSON record list. For each FAIL gate, dispatches to
   a gate-specific diagnostic routine (see catalog below).
3. When the gate's error message alone is not enough, re-runs the
   specific failing sub-command with verbose output — e.g.,
   `python3 -m unittest discover -s tests -v` for Gate 5, or
   `bash -x tests/smoke_test.sh` for Gate 6.
4. Cross-references the collected failure signatures against a
   catalog of known causes (below) so the operator does not have
   to rediscover the common breakages from scratch.
5. Emits a structured markdown report with three columns per
   failing gate: what failed, why (the suspected cause), and a
   concrete fix command ready to copy-paste.

## Diagnostic catalog

Each entry maps a common failure signature to a likely cause and
the fix command that most often resolves it. The mapping is
heuristic — confirm before committing the fix.

- **Gate 1 FAIL: version mismatch.** `falsify.__version__`,
  `pyproject.toml [project.version]`, and the latest
  `## [X.Y.Z]` header in `CHANGELOG.md` disagree. Run
  `grep -n version pyproject.toml CHANGELOG.md falsify.py` to see
  each reading. Fix: align all three to the same semver string in
  one commit.
- **Gate 2 FAIL: `[Unreleased]` empty.** Someone cut a release
  but did not seed a fresh `[Unreleased]` section. Fix: add a
  blank `## [Unreleased]` block above the latest version header
  in `CHANGELOG.md`, even if it just contains a placeholder
  bullet.
- **Gate 3 FAIL: strong tokens leaked.** `XXX`, `FIXME`, or
  `{REPLACE_ME}` reached a tracked, non-exempt file. Fix:
  `git grep -nE '\b(XXX|FIXME|\{REPLACE_ME\})\b'` in the repo,
  then complete or remove each hit before merge.
- **Gate 3 WARN only: `<USER>` / `<VIDEO_URL>` placeholders.**
  Expected pre-GitHub-push / pre-video-upload state. Fix: fill
  these in during the public-push step; no action needed before
  then.
- **Gate 4 FAIL: missing legal file.** `LICENSE`,
  `CODE_OF_CONDUCT.md`, or `.github/SECURITY.md` is gone. Fix:
  `ls LICENSE CODE_OF_CONDUCT.md .github/SECURITY.md` to
  identify the missing path; restore from git history
  (`git log --diff-filter=D --name-only -- <path>`) or
  re-create from the templates directory.
- **Gate 5 FAIL: unittest exit 1.** At least one test regressed.
  Fix: `python3 -m unittest discover -s tests -v 2>&1 | grep -E "(FAIL|ERROR):" | head -20`
  to see which methods fired, then drill into the specific
  `tests/test_<name>.py` file.
- **Gate 6 FAIL: smoke test.** `tests/smoke_test.sh` exited
  non-zero — usually a falsify subcommand returning an
  unexpected exit code after a refactor. Fix:
  `bash -x tests/smoke_test.sh 2>&1 | tail -40` to see the step
  that failed, then run that step by hand to reproduce.
- **Gate 7 FAIL: dogfood.** One of the three self-claims
  (`cli_startup`, `test_coverage_count`, `claude_surface`)
  regressed. Fix: `make self-status` — which calls
  `falsify why <claim>` for each — to see which claim flipped
  and why. A regression is either a real code issue or a
  threshold in need of a principled relock (not a quiet edit).
- **Gate 8 FAIL: docs sanity.** A required doc was deleted or
  became a stub (< 20 lines). Fix: `wc -l docs/*.md *.md` to
  identify the short one; restore content from git history
  (`git log --all -- <path>`) if the file was truncated.
- **Gate 9 FAIL: Claude surface count.** A skill, agent, or
  slash command was removed. Fix:
  `ls .claude/skills/*/SKILL.md .claude/agents/*.md .claude/commands/*.md`
  and restore whichever is missing. Thresholds: >=5 skills,
  >=2 agents, >=3 commands.
- **Gate 10 FAIL: pyproject.** `pyproject.toml` is malformed or
  is missing the `falsify` entry point. Fix:
  `python3 -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text()))"`
  and inspect the dict — in particular
  `project.name == 'falsify'` and `project.scripts.falsify` set.
- **Gate 11 WARN: uncommitted changes.** Working tree is dirty.
  Fix: `git status` then commit or stash before tagging. WARN
  not FAIL because local edits are fine in development; it is
  the tag step that wants a clean tree.
- **Gate 12 FAIL: self-integrity.** A self-claim's `spec.yaml`
  was edited but the lock was not refreshed. Fix:
  `falsify lock claims/self/<claim>/spec.yaml --force`, then
  commit the new `spec.lock.json`.

## Output template

The skill produces a markdown report in this shape:

    # falsify CI doctor report

    **Gates failed:** 2 (5, 7)
    **Gates warned:** 1 (3 — expected pre-GH)
    **Severity:** blocking

    ## Gate 5: test suite (FAIL)
    - Signature: `unittest exit 1`
    - Re-run: `python3 -m unittest discover -s tests -v 2>&1 | grep -E "FAIL:|ERROR:"`
    - Likely cause: test_x assertion regressed after commit abc1234
    - Fix: <specific command>

    ## Gate 7: dogfood (FAIL)
    - Claim affected: cli_startup
    - Why: latest run returned 612ms (threshold: 500ms)
    - Fix: profile falsify CLI cold-start or raise threshold with
      explicit relock

The severity line is `blocking` when any gate is FAIL; it drops
to `advisory` when every non-PASS is a WARN (which is the common
"pre-push placeholders + dirty tree" shape).

## How to invoke

    claude --skill falsify-ci-doctor

Exits 0 if all gates PASS (nothing to diagnose); exits 1 if any
FAIL. The exit code matches `release-check` so the skill is
drop-in as a CI step.

## Boundary with other skills

This skill is a one-shot CI triage; it does not overlap with the
other honesty-focused skills:

- [`claim-review`](../claim-review/SKILL.md) — PR-level diff
  honesty check (unlocked specs, silent threshold edits). Fires
  on diff, not on red CI.
- [`claim-audit`](../claim-audit/SKILL.md) — semantic audit over
  prose (commit messages, README lines, release notes). Fires on
  text input.
- `falsify-ci-doctor` — one-shot triage when CI is red *right
  now*. Fires when `release-check` exits non-zero.

Use `claim-review` or `claim-audit` for honesty; use this skill
for build-breakage.

## Limitations

- **Heuristic, not exhaustive.** The catalog covers the common
  failure shapes; unusual breakages (novel test regressions,
  environment-specific issues, flaky smoke stages) still need
  human judgment.
- **Diagnostic only.** The skill suggests fixes but does not
  apply them. That is deliberate — automatic patches to
  threshold specs or test assertions would defeat the honesty
  discipline falsify is trying to enforce.
- **Depends on `release-check`.** If the CLI itself is broken
  (argparse error, import failure, stdlib gap), `release-check`
  cannot run and this skill has no signal. Fall back to raw
  `python3 falsify.py --version` and `python3 -m unittest
  discover -s tests` in that case.
