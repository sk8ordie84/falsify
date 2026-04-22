---
description: "Run the claim-audit skill to semantically cross-check all claims in this repo, then summarize findings."
allowed-tools: "Bash(git:*), Bash(python3:*), Bash(falsify:*), Read, Glob, Grep"
---

# /audit-claims

## Goal

Produce a single markdown audit report covering every claim in the
repo — aggregate state, honesty score, and semantic findings from
the `claim-audit` skill — so a reviewer can decide whether the
claim surface is shippable.

## When to use

- Pre-release, before cutting a `v*.*.*` tag.
- During review of any PR that touches `claims/`,
  `examples/**/spec.yaml`, or a metric module.
- On a quarterly cadence as a standing honesty check, independent
  of any specific change.

## Steps

1. Enumerate every known claim:

        falsify list --json

   Capture the name, lock status, and latest verdict per entry.
2. Aggregate the state counts:

        falsify stats --json

   Record PASS / FAIL / INCONCLUSIVE / STALE / UNRUN / UNLOCKED
   totals.
3. Compute the honesty score:

        falsify score --format json

   Note both the numeric score and the status band
   (`pass` / `warn` / `fail`).
4. Invoke the `claim-audit` skill in a forked context, passing the
   full verdict-store snapshot from Steps 1-3. The fork keeps the
   parent token budget clean; the skill returns a structured list
   of findings with severity levels (critical / warn / info).
5. Merge every output into one markdown report. Sections, in order:
    - **Aggregate** — one-line counts table.
    - **Honesty score** — number, status, threshold.
    - **Findings by severity** — grouped; each finding gets claim
      name, one-line description, and a cited source
      (spec.yaml line, verdict field, etc.).
    - **Recommended actions** — ranked by urgency. Critical items
      first, each with a concrete `falsify <subcommand>` to run.

## Output format

A single markdown document. No raw JSON blobs in the final report
— if a reviewer wants raw data they can re-run the subcommands
directly. Keep the report readable on a single screen when
possible; link to `docs/FAQ.md` for objection context.

## See also

- Skill `claim-audit` — the lightweight regex+keyword audit this
  command invokes.
- Subagent `claim-auditor` — the heavier semantic reviewer that
  `claim-audit` escalates to when needed.
- `CLAUDE.md` — Prime Directive: every claim is locked BEFORE it
  is run.
- `TUTORIAL.md` — first-time walkthrough of the claim lifecycle.
