---
name: claim-review
description: Review a git diff (staged, unstaged, or PR branch vs base) for falsify honesty violations. Flags new specs that aren't locked, threshold changes without relock, metric_fn references to nonexistent modules, and stale lock files. Call this skill before merging any PR that touches claims/*.yaml or metric files.
allowed-tools:
  - "Bash(git:*)"
  - "Bash(python3:*)"
  - Read
  - Glob
  - Grep
context: fork
---

# claim-review

Fast, syntactic honesty-diff check for pull requests that touch
claims or metric code. Reports on what the diff *changed* about
the lock/relock discipline — not whether the claims themselves are
scientifically sound. That deeper pass is the
[`claim-auditor`](../../agents/claim-auditor.md) subagent's job.

## When to use

- Before merging a PR that touches `claims/`, `examples/*/spec.yaml`,
  or any metric module.
- As a pre-review gate on draft PRs — catch missing locks before a
  human reviewer has to spot them.
- Whenever `falsify doctor` reports inconsistencies that a human
  thinks came from a recent diff.

## What this skill does

1. Runs `git diff <base>...HEAD` (or reads the staged diff if no
   base is given) to collect the set of changed files.
2. Identifies files under `claims/`, `examples/*/spec.yaml`, or any
   other `*.yaml` whose body mentions `failure_criteria` — those
   are the claim specs in scope.
3. For each touched spec, checks whether a corresponding
   `spec.lock.json` exists *and* whether the canonical hash of
   the current spec matches the hash in that lock.
4. Flags `threshold`, `direction`, or `metric` changes inside
   `failure_criteria` as **CRITICAL** — they demand an explicit
   `falsify lock --force` with a fresh hash that anyone can audit
   after the fact.
5. Cross-checks every `experiment.metric_fn` reference in a
   touched spec to confirm the `module:function` target resolves
   to a real, importable Python callable.
6. Writes a short Markdown review comment to stdout summarising
   the findings by severity.

## How to invoke

```
claude --skill claim-review <base-ref>
```

Default `<base-ref>` is `origin/main`. Override via the
`CLAUDE_CLAIM_REVIEW_BASE` environment variable — CI workflows
typically set this to `${{ github.base_ref }}` for PR runs.

The skill never modifies the repo. It only reads the diff and
posts its findings to stdout; the calling CI step decides whether
to block the merge.

## Severity levels

- **CRITICAL** — `threshold`, `direction`, or `metric` changed in
  a spec without a matching re-lock (`spec.lock.json`'s hash no
  longer matches the spec's canonical YAML).
- **CRITICAL** — a new spec was added under `claims/` or
  `examples/*/spec.yaml` with no corresponding `spec.lock.json`
  at all.
- **WARNING** — lock file timestamp is older than the spec's file
  timestamp on disk, suggesting silent post-lock edits that a
  canonical-hash check might still miss under edge cases.
- **WARNING** — `experiment.metric_fn` points at a Python module
  or attribute that cannot be imported in the current tree.
- **INFO** — lock file present and matches the spec. Explicit
  green light, noted so reviewers see the positive case.

## Output format

An example comment the skill might post on a PR:

    # Claim review — 2 findings
    
    ## CRITICAL
    - `claims/juju/spec.yaml` — `failure_criteria.threshold` changed
      `0.25 → 0.20` without a matching re-lock. Run
      `falsify lock juju --force` to regenerate `spec.lock.json`
      and commit the new hash alongside this change.
    
    ## INFO
    - `claims/retrieval-recall/spec.yaml` — lock present and hash
      matches. No action needed.

Findings are listed severity-first; if every finding is INFO, the
comment body is a single green-light line.

## Exit codes

- `0` — only INFO and/or WARNING findings.
- `1` — at least one CRITICAL finding. CI wraps this exit code
  into a merge block on the PR.

## Boundary with claim-auditor subagent

`claim-review` is fast and syntactic — it examines the diff, not
the claim's semantics. The
[`claim-auditor`](../../agents/claim-auditor.md) subagent performs
the deeper, cross-repo semantic audit (does the claim text still
hold across every artefact that references it?) and is meant for
nightly jobs, not per-PR. Run the review on every PR; run the
audit on a schedule. Don't confuse them — they guard different
failure modes.

## Limitations

- Does **not** re-run any experiment. `falsify run` / `verdict`
  is a separate pass.
- Does **not** evaluate metric correctness beyond confirming the
  `metric_fn` import resolves; a metric that imports but returns
  garbage is out of scope here.
- Only sees what's in the current working tree plus the base ref.
  External data changes that affect a metric's output but leave
  the spec hash intact will be caught by the nightly audit, not
  by this skill.
