---
name: hypothesis-author
description: Use when the user makes an empirical claim (e.g., "X improves Y", "our filter works", "results show…") and hasn't yet written a falsifiable spec. Converts natural-language claims into a locked hypothesis.yaml. Triggers on phrases like "I believe", "our data shows", "this works", "we proved", "testing whether", "hypothesis".
allowed-tools: Read Write Bash(python3 falsify.py *)
---

# hypothesis-author

Turn a natural-language claim into a pre-registered, falsifiable spec
that the Falsification Engine can lock, run, and verdict.

## When to activate

Fire this skill when the user does any of the following, *and* a
corresponding `spec.yaml` doesn't already exist under `.falsify/`:

- States an empirical claim they want to defend:
  *"our retrieval step is faster"*, *"the new prompt is more accurate"*,
  *"this filter reduces hallucinations"*.
- Uses hypothesis-shaped language: *"I believe"*, *"our data shows"*,
  *"we proved"*, *"testing whether"*, *"the hypothesis is"*.
- Reports a result they want to commit to: *"the benchmark came back
  at 0.87 — that beats baseline"*.

Do **not** activate when:

- The user is asking a question or debugging.
- A `.falsify/<name>/spec.yaml` already exists for the claim — in that
  case, point them at `falsify lock` / `falsify run` instead.
- The claim is explicitly aspirational or rhetorical (*"we should try
  to…"*, *"wouldn't it be great if…"*).

## The 5-question dialogue

Walk the user through exactly these five prompts, in order. Don't skip;
don't batch. Each answer narrows the spec.

1. **Claim.** *"In one sentence, what are you asserting? Phrase it so
   someone could, in principle, prove you wrong."* Push back on vague
   nouns ("better", "faster", "improved") until the sentence names a
   concrete metric and a concrete comparison.

2. **Metric.** *"How will you measure that? What is the metric's name,
   and what does a higher/lower value mean?"* If they don't have a
   metric in mind, stop and surface the gap — the claim is not yet
   falsifiable.

3. **Dataset.** *"What data will the metric be computed on?"* Pin down
   a path, a dataset ID, or a deterministic fixture. "Production
   traffic" is not acceptable unless sampled deterministically.

4. **Threshold & direction.** *"What number, with which direction,
   would have to hold for the claim to count as confirmed? What would
   falsify it?"* Produce exactly one `{direction, threshold}` pair
   unless the user insists on multiple criteria.

5. **Stopping rule.** *"When do you stop collecting evidence?"* Fix a
   number of samples, epochs, or a time budget — locked in up front so
   no one can stop early on a favourable reading.

## Falsifiability checklist

Before writing the spec, walk this list aloud with the user. If any
check fails, loop back to the relevant dialogue question.

- [ ] **Not circular.** The threshold was decided *before* observing
      any data — it isn't just "the number we saw, minus epsilon".
- [ ] **Not subjective.** No "looks good", "seems reasonable", "feels
      right" — the metric is computed, not judged.
- [ ] **Not a moving target.** The stopping rule is fixed; the user
      commits to it before locking.
- [ ] **Measurable with current tooling.** A `metric_fn(run_dir)` can
      actually be written against the artifacts produced by the
      experiment command.
- [ ] **Could conceivably fail.** Ask: "what result would convince you
      the claim is wrong?" If the user can't answer, the claim is not
      yet falsifiable.

## Spec generation template

Pick a short kebab-case `<name>` from the claim (e.g.
`retrieval-recall-above-85`). Write to
`.falsify/<name>/spec.yaml` using this shape, substituting every
placeholder with the values gathered in the dialogue:

```yaml
claim: "<one-sentence claim from Q1>"

falsification:
  failure_criteria:
    - metric: <metric name from Q2>
      direction: <above|below|equals>
      threshold: <number from Q4>
  minimum_sample_size: <integer from Q5>
  stopping_rule: "<stopping rule from Q5>"

experiment:
  command: "<shell command that produces the run artifacts>"
  dataset: "<dataset path or id from Q3>"
  metric_fn: "<module:function>"

environment:
  python: "3.11"
  packages: []
```

Double-check before writing:

- No angle-bracket placeholders remain.
- `direction` is one of `above`, `below`, `equals`.
- `metric_fn` is in `module:function` form and the module is importable
  from the project root.
- `claim` is a single sentence, not a paragraph.

## Hand-off

After the file is written, print a short, literal hand-off so the user
knows the exact next commands:

```
Spec written to .falsify/<name>/spec.yaml

Next steps:
  1. Review the spec once more.
  2. Pre-register it:   python3 falsify.py lock <name>
  3. Run the experiment: python3 falsify.py run <name>
  4. Get the verdict:   python3 falsify.py verdict <name>
```

Do not run `lock` automatically — pre-registration is a deliberate
commitment the user has to make themselves.
