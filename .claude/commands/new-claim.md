---
description: "Scaffold, lock, and run a new falsify claim from a template in one guided flow."
argument-hint: "<template-name> [claim-name]"
allowed-tools: "Bash(python3:*), Bash(falsify:*), Read, Write, Edit"
---

# /new-claim

## Goal

Take a user from "I want to make an empirical claim" to a locked,
run, verified falsify claim in a single guided flow.

## When to use

- The user names a measurable property they want to gate on (e.g.
  "classifier accuracy above 0.85") and has no spec yet.
- You are onboarding a teammate to the falsify discipline for the
  first time — this command walks every step.
- A PR introduces a new claim domain that maps to one of the
  shipped templates.

## Steps

1. Parse `$1` as the template name. Valid values are exactly:
   `accuracy`, `latency`, `brier`, `llm-judge`, `ab`. Abort with a
   list of valid templates if `$1` is missing or unrecognized.
2. Parse `$2` as the optional claim name. Default to `$1` when
   omitted. Claim names must match `[a-zA-Z0-9_-]+`.
3. Scaffold the claim:

        falsify init --template "$1" --name "$2"

   This creates `claims/$2/` (spec + metric + data) and a mirrored
   `.falsify/$2/spec.yaml`.
4. Open `claims/$2/spec.yaml` and `.falsify/$2/spec.yaml` for the
   user. Summarize the threshold, direction, and dataset path in
   plain English. Ask: "edit any of these before locking?" If the
   user wants changes, apply them with Edit and re-display.
5. Lock the spec:

        falsify lock "$2"

   Capture the printed spec hash; read back `.falsify/$2/spec.lock.json`
   to confirm `spec_hash` is present.
6. Run the experiment:

        falsify run "$2"

   Relay stdout to the user — non-zero exit means the subprocess
   itself failed and should be diagnosed before proceeding.
7. Compute the verdict:

        falsify verdict "$2"

   Exit 0 is PASS, exit 10 is FAIL, exit 2 is INCONCLUSIVE. Report
   the observed value and threshold in one line.
8. If the verdict was FAIL or INCONCLUSIVE, immediately run:

        falsify why "$2"

   and present the diagnosis plus the suggested next honest action.

## Stop conditions

- `$1` is missing or not one of the five valid templates.
- User declines to proceed after reviewing the spec in Step 4.
- `falsify lock` exits non-zero (placeholder marker left in spec,
  file unreadable, etc.) — surface the stderr and stop.
- `falsify run` fails with a non-falsify exit code — the
  experiment command itself is broken; do not fabricate a verdict.

## See also

- Skill `falsify` — the orchestrator this command invokes step by
  step.
- Skill `hypothesis-author` — use before `/new-claim` when the
  user hasn't decided on threshold or metric yet.
- `CLAUDE.md` — Prime Directive: every claim is locked BEFORE it
  is run.
- `TUTORIAL.md` — the long-form walkthrough for newcomers.
