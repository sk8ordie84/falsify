# PR honesty review with `claim-review`

Silent threshold lowering is the single highest-leverage attack
surface on a pre-registered claim store: a spec gets locked at
`threshold: 0.85`, a convenient PR quietly drops it to `0.80`,
and nobody notices because the YAML diff is one character. The
[`claim-review`](../.claude/skills/claim-review/SKILL.md) Claude
skill exists to make that failure mode loud.

## Why claim review matters

The commit-msg guard catches *affirmative* commit messages that
contradict a logged verdict; the nightly
[`claim-auditor`](../.claude/agents/claim-auditor.md) subagent
does semantic cross-referencing across every artefact in the
repo. Neither of those catch "goalpost moved in a diff that also
edits something else." That's what this skill is for.

## Setup (GitHub Actions)

Wire the skill into a PR check. Example:

```yaml
name: PR claim review

on:
  pull_request:
    paths:
      - "claims/**"
      - "examples/**/spec.yaml"
      - "**/metric*.py"

jobs:
  claim-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # need the base ref for the diff
      - uses: anthropics/claude-code-action@v1
        with:
          skill: claim-review
          args: ${{ github.base_ref }}
        env:
          CLAUDE_CLAIM_REVIEW_BASE: origin/${{ github.base_ref }}
```

Exit code `1` from the skill blocks the merge. `0` posts the
findings comment and lets the PR proceed.

## Before / after examples

### CRITICAL — threshold silently lowered

Before:

    failure_criteria:
      - metric: accuracy
        direction: above
        threshold: 0.85

After (in the PR diff):

    failure_criteria:
      - metric: accuracy
        direction: above
        threshold: 0.80

The `spec.lock.json` in the same directory still carries the old
canonical hash. `claim-review` emits:

    ## CRITICAL
    - `claims/retrieval-recall/spec.yaml` — `failure_criteria.threshold`
      changed `0.85 → 0.80` without a matching re-lock. Run
      `falsify lock retrieval-recall --force` to regenerate
      `spec.lock.json` and commit the new hash with this change.

### INFO — honest rewording

If the author tightened the threshold to `0.87` *and* re-ran
`falsify lock --force` so `spec.lock.json` carries the fresh
canonical hash, the skill notes the lock-in and gets out of the
way:

    ## INFO
    - `claims/retrieval-recall/spec.yaml` — threshold changed;
      spec.lock.json hash updated to match (`3f1a…b2`). Honest
      re-lock. No action needed.

## FAQ

**Why not a git hook?** Hooks run pre-commit on one machine and
see only what's on disk. They don't have cross-file semantic
awareness of "this spec change wasn't accompanied by a lock
update" across arbitrary PR diffs.

**Why not the existing commit-msg guard?** That guard catches
affirmative language in commit messages against logged verdicts
("we've proven X works" when X's last verdict was FAIL). It does
not read the diff itself. Different failure mode; complementary.

**Does it replace human review?** No. It removes the single
class of violation that's mechanical (unlocked / mismatched
hash). Everything else — does the metric measure what the author
claims? is the threshold defensible? — stays with the human.

## See also

- The skill itself:
  [`.claude/skills/claim-review/SKILL.md`](../.claude/skills/claim-review/SKILL.md)
- Semantic nightly auditor:
  [`.claude/agents/claim-auditor.md`](../.claude/agents/claim-auditor.md)
- Commit-msg guard: `hooks/commit-msg` and
  [`falsify guard`](../falsify.py) in the CLI.
