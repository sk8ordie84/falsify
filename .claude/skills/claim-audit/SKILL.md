---
name: claim-audit
description: Scans provided text for empirical claims and checks them against locked verdicts. Trigger phrases "audit this claim", "check this text", "is this accurate", "does this match our verdicts", "review this PR description", "lint this commit message", "fact check against falsify".
allowed-tools: Read, Glob, Grep, Bash
disable-model-invocation: false
context: fork
---

# claim-audit

Lightweight in-session text auditor. Runs a fast keyword + regex pass
over arbitrary text — commit messages, README sections, PR descriptions,
release notes, tweets — and cross-references any empirical claim it
finds against the verdict log at `.falsify/*/verdict.json`.

This skill is the *first-pass* filter. It's deliberately cheap: string
matching on metric names, numeric thresholds, and negation cues. When
that's enough, you get a clean table and move on. When it isn't — too
many claims, paraphrases, or low-confidence matches — the skill hands
off to the `claim-auditor` subagent, which does the semantic reasoning.

## When to activate

Fire this skill when the user presents text that is about to become
part of a visible artifact — a commit, a PR body, a README edit, a
release note, an external post — and asks for a sanity check before
it goes out.

Typical openings:

- *"audit this claim"*, *"can you check this text?"*
- *"is this accurate against what we've actually measured?"*
- *"lint this commit message before I push"*
- *"review this PR description"*
- *"does this match our verdicts?"*
- *"fact check against falsify"*

Do *not* fire when:

- The user is writing code or prose that makes no empirical claims.
- No `.falsify/` directory exists in the repo — there's nothing to
  check against; point the user at `falsify init` instead.
- The user has already run `falsify guard` on the same text — guard
  covers the coarse case; escalate to the `claim-auditor` subagent if
  they want depth.

## Workflow

Execute in order; stop as soon as you have enough signal to emit the
table.

1. **Load the verdict log.** Use `Glob` to find every
   `.falsify/*/verdict.json`. For each file, read it and also read
   the sibling `.falsify/<name>/spec.yaml` to recover the full claim
   text. Build an in-memory table keyed by spec name with: claim
   text, `metric`, `direction`, `threshold`, `verdict` state (`PASS`
   / `FAIL` / `INCONCLUSIVE`), and `checked_at`. Compute `STALE` for
   any verdict whose `checked_at` is more than 7 days old.

2. **Scan the input text for empirical claims.** Three cheap passes:
   - **Numeric thresholds.** Regex `\d+(\.\d+)?%?` pulls every
     number in the text. Each hit is a candidate claim anchor.
   - **Metric keyword match.** For each loaded spec, check whether
     its `metric` name (e.g. `accuracy`, `brier_score`, `recall`)
     appears as a whole word in the text. If yes, link the numeric
     anchor to that spec.
   - **Negation cues.** Scan for *"not"*, *"doesn't"*, *"no longer"*,
     *"regress"*, *"below"* / *"above"* / *"under"* / *"over"*.
     These flip the effective direction of a claim and are needed to
     match paraphrases like *"error rate below 0.15"* against a spec
     tracking accuracy above 0.85.

3. **Rank each match by confidence.**
   - **HIGH** — metric name *and* a compatible numeric threshold
     both appear, and direction aligns with the spec.
   - **MED**  — metric name present, threshold missing or off by a
     small amount, or direction implicit.
   - **LOW**  — a claim-shaped sentence exists with no obvious
     anchor in the loaded specs. Could be UNSUPPORTED, could be a
     paraphrase only semantic reasoning will catch.

4. **Emit the table** (see next section). Record each extracted
   claim with its matched spec, the verdict state, and the
   confidence level.

5. **Decide whether to escalate.** If any of the following hold,
   recommend the `claim-auditor` subagent for a deeper pass:
   - more than two candidate claims;
   - any row marked LOW confidence;
   - the text reads like a paraphrase of a spec rather than a
     literal restatement;
   - the input is long (> ~30 lines of prose) — regex coverage is
     naturally shallow past that.

## Output format

Emit a compact Markdown table, one row per extracted claim, followed
by a single-line verdict:

```
| Input claim                              | Matched spec         | Verdict state | Confidence |
|------------------------------------------|----------------------|---------------|------------|
| "accuracy above 90%"                     | acc_spec             | PASS          | HIGH       |
| "brier score below 0.25"                 | juju                 | PASS          | HIGH       |
| "it always works"                        | —                    | —             | LOW        |

✅ 2/3 claims match a PASS verdict. 1 claim unsupported — consider handing off to the `claim-auditor` subagent for semantic review, or register it with `falsify init`.
```

Verdict-line legend:

- **✅** — every claim in the text lines up with a fresh PASS verdict.
- **⚠️** — there's at least one UNSUPPORTED, STALE, or LOW-confidence
  row. The text isn't wrong; it isn't backed either.
- **❌** — at least one row is marked CONTRADICTS (matched spec has a
  FAIL or INCONCLUSIVE verdict). Strongly recommend blocking whatever
  action the text was being prepared for.

If the text contains no empirical claims, output a single line:
*"No empirical claims detected — nothing to audit."*

## Hand-off to claim-auditor subagent

The keyword pass misses paraphrases. When the scan returns `>2` claims,
any LOW-confidence row, or suspected paraphrasing, invoke the
`claim-auditor` subagent via the `Task` tool and pass the full input
text plus the loaded verdict summary as context. The subagent does
the semantic cross-reference this skill deliberately skips.

Make the handoff explicit in the output so the user sees the chain of
responsibility:

> "⚠️ Confidence is LOW on 2 of 4 rows — paraphrases suspected.
> Escalating to the `claim-auditor` subagent for a semantic pass…"

Don't duplicate work: when you escalate, stop emitting your own table
and let the subagent's richer output stand.

## Examples

### (a) README line: HIGH-confidence PASS

> **User:** Lint this README sentence before I merge:
> *"Our retrieval reranker maintains accuracy above 90%."*
>
> **Assistant:** *(loads `.falsify/*/verdict.json`; matches `acc_spec`
> with `metric=accuracy`, `direction=above`, `threshold=0.90`,
> `verdict=PASS`, `checked_at=1d old`)*
>
> | Input claim                                  | Matched spec | Verdict state | Confidence |
> |----------------------------------------------|--------------|---------------|------------|
> | "accuracy above 90%"                         | acc_spec     | PASS          | HIGH       |
>
> ✅ 1/1 claim matches a PASS verdict. Safe to merge.

### (b) Tweet draft: UNSUPPORTED

> **User:** Audit this tweet: *"our new agent always works on edge cases"*
>
> **Assistant:** *(no spec matches "always works on edge cases")*
>
> | Input claim                                  | Matched spec | Verdict state | Confidence |
> |----------------------------------------------|--------------|---------------|------------|
> | "it always works on edge cases"              | —            | —             | LOW        |
>
> ⚠️ UNSUPPORTED. There's no locked spec backing this claim. Either
> register a falsifiable hypothesis first
> (`python3 falsify.py init edge-case-coverage`, then the
> `hypothesis-author` skill), or soften the language before posting.
