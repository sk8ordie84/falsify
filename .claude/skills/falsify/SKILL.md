---
name: falsify
description: Triggers when user makes empirical claims or asks to verify results. Trigger phrases include "testing whether", "let's verify", "does this work", "is it true that", "empirical claim", "I think X performs better", "run the experiment", "check the threshold", "verdict", "falsify this".
allowed-tools: Bash, Read, Write, Edit, Glob
disable-model-invocation: false
context: fork
---

# falsify

Orchestrator skill for the Falsification Engine. Routes any empirical
claim the user makes — or any "does X actually work?" question — to
the right step in the init → lock → run → verdict pipeline, and hands
off to the `hypothesis-author` skill when a new spec needs to be
drafted.

## When to activate

Fire this skill when the user does any of the following:

- **Asserts a measurable claim** about behaviour, metrics, performance,
  accuracy, or correctness: *"this prompt is more accurate"*,
  *"our retriever is faster"*, *"the threshold is high enough"*.
- **Asks "does X work?"** or any variant that expects an empirical
  answer: *"does this work?"*, *"is it true that the filter blocks
  profanity?"*, *"let's verify that the reranker helps"*.
- **Wants to lock a hypothesis** they've already drafted or wants to
  pre-register a claim before gathering evidence.
- **Asks for a verdict** on a prior run: *"what's the verdict?"*,
  *"did that experiment pass?"*, *"falsify this for me"*.

Do *not* activate when the user is reading code, debugging a stack
trace, or asking a definitional question that doesn't involve a
measurable claim.

## Routing logic

Apply this decision tree in order. Stop at the first branch that
matches.

1. **No `.falsify/` directory in the current working directory.**
   Offer to scaffold the first claim:

   ```
   python3 falsify.py init <name>
   ```

   Suggest a short kebab-case `<name>` derived from the claim, then
   fall through to step 4 so the spec gets real values.

2. **`.falsify/<name>/spec.yaml` exists but no `spec.lock.json`.**
   The claim has been drafted but not pre-registered. Offer:

   ```
   python3 falsify.py lock <name>
   ```

   Surface any placeholder-guard or schema errors verbatim — they tell
   the user exactly which fields still need real values.

3. **`spec.lock.json` exists and the user's claim fuzzy-matches an
   existing `spec.yaml`'s `claim` field.** Run the pipeline:

   ```
   python3 falsify.py run <name>
   python3 falsify.py verdict <name>
   ```

   If `run` reports a hash mismatch (exit 3), the spec has drifted
   since it was locked — surface this and ask whether the drift is
   legitimate before suggesting `lock --force`.

4. **The claim doesn't match any locked spec.** Hand off to the
   `hypothesis-author` skill (see below) with the user's raw claim
   text as the seed. That skill owns the five-question dialogue and
   produces a new `.falsify/<name>/spec.yaml`. After it finishes,
   resume at step 2.

5. **After `verdict` returns**, translate the exit code so the user
   knows what happened without having to read the CLI output:

   - `0` → **PASS**: every failure criterion held.
   - `10` → **FAIL**: at least one criterion was violated.
   - `2` → **INCONCLUSIVE**: usually `minimum_sample_size` wasn't met,
     or the spec is malformed. Check `verdict.json` for `reason`.
   - `3` → **HASH_MISMATCH**: `spec.yaml` changed after `lock`.
     Either revert the edit or `lock --force` if the change is
     intentional and pre-registered semantics can be abandoned.
   - `11` → **guard violation**: reserved for `falsify guard`
     blocking a commit message.

## Hook installation

After a first successful `lock`, offer to install the commit-msg hook
so future commits can't slip affirmative language past a failing
claim:

```bash
cp hooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Or as a symlink, so hook updates propagate automatically:

```bash
ln -sf "$(pwd)/hooks/commit-msg" .git/hooks/commit-msg
```

Explain the payoff in one sentence: the hook prevents committing
messages that contradict the logged verdict — e.g., a commit saying
*"confirmed the retriever beats baseline"* while the latest verdict
for that claim is `FAIL` or `INCONCLUSIVE`.

Only offer this once per repo. If `.git/hooks/commit-msg` already
exists, skip the suggestion.

## Hand-off to hypothesis-author

When step 4 fires — the user has a claim but no matching spec —
delegate to the `hypothesis-author` skill. Pass the claim verbatim as
the seed; that skill will run its own five-question dialogue and
produce the `.falsify/<name>/spec.yaml` file.

When `hypothesis-author` returns, don't re-draft. Resume at step 2
of the routing logic: suggest `falsify lock <name>` using the `<name>`
that `hypothesis-author` chose.

## Examples

### (a) Fresh claim, no `.falsify/` yet

> **User:** I think our new reranker performs better than the baseline.
>
> **Assistant:** That's an empirical claim — let's pre-register it
> before gathering evidence so the threshold can't move later.
> There's no `.falsify/` directory here yet, so I'll hand this to the
> `hypothesis-author` skill, which will walk us through five
> questions (claim / metric / dataset / threshold+direction /
> stopping rule) and write the spec to
> `.falsify/reranker-beats-baseline/spec.yaml`.
>
> *(hypothesis-author runs, produces spec.yaml)*
>
> **Assistant:** Spec drafted. When you're ready:
> `python3 falsify.py lock reranker-beats-baseline`

### (b) Existing locked spec, request for verdict

> **User:** Did the retrieval-recall-above-85 experiment pass?
>
> **Assistant:** There's a locked spec at
> `.falsify/retrieval-recall-above-85/spec.lock.json`. Running the
> pipeline now:
>
> ```
> python3 falsify.py run retrieval-recall-above-85
> python3 falsify.py verdict retrieval-recall-above-85
> ```
>
> *(outputs: `Verdict: PASS`, exit 0)*
>
> **Assistant:** **PASS** — the criterion `recall above 0.85` held
> on the observed value. `.falsify/retrieval-recall-above-85/verdict.json`
> has the full record for future `guard` scans.
