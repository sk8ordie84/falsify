---
description: "Validate a claim is ready to ship: locked, passing, fresh, reproducible via replay. Gate for release."
argument-hint: "<claim-name>"
allowed-tools: "Bash(python3:*), Bash(falsify:*), Read"
---

# /ship-verdict

## Goal

Gate a single claim against four hard checks — locked, passing,
fresh, reproducible — before a human decides to ship. This command
does NOT ship anything; it only answers "is this claim releasable
as of right now?"

## When to use

- Pre-release, as the last check before tagging a version or
  rolling out a feature that depends on the claim.
- Pre-merge on a PR that changes a production-critical claim
  whose verdict is load-bearing for the release.

## Steps

1. Verdict gate:

        falsify verdict "$1"

   Must exit `0` (PASS). On exit `10` (FAIL) or `2`
   (INCONCLUSIVE) abort and print the observed value plus the
   remediation: "re-run after fixing the experiment" or "lower
   `minimum_sample_size`" as appropriate.
2. Freshness gate:

        falsify why "$1" --json

   Parse the `state` field. Must be `PASS`. Any other state
   (especially `STALE`) aborts. For `STALE` advise:
   `falsify run "$1" && falsify verdict "$1"` to refresh.
3. Locate the latest run directory under
   `.falsify/$1/runs/` — sort lexicographically and pick the last
   entry. Extract its `<run-id>` (the directory name).
4. Replay gate:

        falsify replay "<run-id>"

   Must exit `0` (reproducible). A non-zero exit means the stored
   metric value no longer matches what the metric function
   produces against the stored run directory; the claim is not
   reproducible and must not ship.
5. Audit-chain gate:

        falsify export --name "$1" --output /tmp/ship-$$.jsonl
        falsify verify /tmp/ship-$$.jsonl --strict

   Must exit `0`. A break in the hash chain means some prior
   lock, run, or verdict record was tampered with or reordered
   since it was written.
6. If every gate passed, print exactly:

        SHIP: $1 is locked, passing, fresh, and reproducible.

   and exit `0`.
7. If any gate failed, print the failing gate, its exit code, and
   the one-line remediation from Step 1-5. Exit `1`.

## Stop conditions

Any gate failure aborts the remaining checks — do not continue
past the first failure. The goal is a precise diagnosis of the
blocker, not a laundry list.

This command is a verification gate only. It does not `git push`,
`git tag`, call any release API, or modify any artifact. Shipping
remains a manual human action after the gate passes.

## See also

- Skill `falsify` — the orchestrator for the lock-run-verdict
  pipeline this command audits.
- `CLAUDE.md` — Prime Directive: every claim is locked BEFORE it
  is run. This command enforces the "and stays locked" corollary.
- `TUTORIAL.md` — the claim lifecycle from zero to first verdict.
