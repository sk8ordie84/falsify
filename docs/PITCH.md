# Pitch copy bank

Use these for different channels. Each is self-contained — copy the
one whose length matches the slot.

## 15-word hook (video opener, tweet, email subject)

> Git for AI honesty — lock the claim before the data, or it didn't happen.

## 30-word teaser (social post caption, podcast plug)

> Your AI agent lied to you last Tuesday. You didn't catch it because
> you didn't lock the claim first. Falsification Engine turns every
> AI claim into a deterministic, hash-anchored, CI-gated artifact.

## 60-word elevator (form fields with short limits, Product Hunt blurb)

> Falsification Engine is a CLI that forces scientific
> pre-registration on AI-agent claims. You declare the metric and
> threshold before running anything; a SHA-256 hash freezes the
> spec. The verdict is a deterministic exit code — 0 PASS, 10 FAIL,
> 3 tampering detected. A git hook blocks commit messages that
> contradict locked verdicts. MIT, stdlib + pyyaml.

## 120-word pitch (HackerNews Show HN, Reddit r/programming)

> Falsification Engine is a CLI that forces scientific
> pre-registration on AI-agent claims. You declare the metric,
> direction, and threshold before running anything; a SHA-256
> canonical-YAML hash freezes the spec. The verdict is a
> deterministic exit code — `0` PASS, `10` FAIL, `3` if someone
> tampered with the spec after locking. A commit-msg git hook
> blocks commits whose messages contradict a locked verdict.
>
> The repo ships a 20-row JUJU prediction-ledger fixture that runs
> lock → run → verdict end-to-end in under 100ms and demonstrates
> a Brier-score PASS. Three Claude Code skills (hypothesis-author,
> falsify orchestrator, claim-audit) handle spec drafting and text
> audit; two forked-context subagents (claim-auditor,
> verdict-refresher) do the heavier semantic and maintenance work.
> A GitHub Actions workflow re-verdicts every push. `./demo.sh`
> walks the full PASS → tamper → FAIL → guard-block story in about
> ten seconds.
>
> MIT, stdlib + pyyaml, `pip install .`. Built for the Anthropic
> Built with Opus 4.7 hackathon, April 2026.

## 200-word pitch (submission form — canonical)

The canonical 200-word version lives in
[SUBMISSION.md](../SUBMISSION.md) under "Short description
(submission form)". **If you update this variant, update
SUBMISSION.md too — they must match.**

## Video script opener (spoken, 12 seconds)

> AI agents make claims. They rarely say what threshold they mean.
> They never tell you when they decided. This tool forces them to.

## Twitter launch thread (5 tweets)

**Tweet 1 — hook**

> Git for AI honesty — lock the claim before the data, or it
> didn't happen. 1/5

**Tweet 2 — problem**

> Agents output "my model gets 92 percent accuracy." Against what
> threshold? Decided when? Post-hoc rationalization is the default.
> 2/5

**Tweet 3 — solution**

> Falsify forces pre-registration. Declare threshold → SHA-256
> lock → run → deterministic exit code. Tamper the spec, hash
> mismatch catches it. 3/5

**Tweet 4 — Opus 4.7 layer**

> Three Claude Code skills draft the spec, route the workflow,
> audit text against verdicts. Two forked-context subagents handle
> semantic audit and stale-verdict refresh. 4/5

**Tweet 5 — CTA**

> MIT, stdlib + pyyaml, `pip install .` — link to repo. Built for
> the Anthropic Opus 4.7 hackathon. 5/5

## Press one-liner (for if a newsletter picks it up)

> Falsification Engine: a git hook that calls bullshit on AI
> claims before you commit them.

## Anti-patterns to avoid in any pitch

- **Do not lead with "deterministic exit codes"** — too technical
  for the first ten seconds. Save it for the 60-word elevator
  onward.
- **Do not use the word "framework"** — this is a CLI, not a
  framework. Frameworks imply adoption cost; CLIs imply a binary
  you pipe into.
- **Do not say "we use AI to check AI"** — the point is that the
  tool is deterministic. AI drafts the spec; the hash and the exit
  code rule on the verdict. Muddling this undermines the whole
  pitch.
- **Do not call it "scientific" in the hook** — people glaze over.
  Use "honesty" or "tripwire" or "lock" instead. "Scientific"
  belongs in the 120-word pitch, not the 15-word one.
- **Do not pitch as an academic tool** — pitch as a dev-ops tool
  that *happens* to be scientifically rigorous. The jurors have
  shipped software; speak that language first.
