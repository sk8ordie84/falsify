# Submission — Falsification Engine

## Project name

Falsification Engine

## One-line tagline

Pre-registration and CI for AI-agent claims — deterministic PASS or
FAIL, not a story.

## Short description (submission form)

**Your AI agent lied to you last Tuesday. You didn't catch it
because you didn't lock the claim first.**

Falsification Engine is git for AI honesty. Before you run the
experiment, you declare the claim, the metric, and the threshold.
A SHA-256 hash freezes the spec. Then you run, and the verdict is
deterministic — PASS, FAIL, or hash mismatch if someone tampered.
A commit-msg git hook blocks any commit whose message contradicts
the locked verdict.

Eight CLI subcommands, a CI workflow that re-verdicts every push,
three Claude Code skills (hypothesis-author, falsify orchestrator,
claim-audit), and two forked-context subagents (claim-auditor for
semantic cross-reference, verdict-refresher for autonomous
stale-verdict maintenance). Opus 4.7's long context handles the
full repo plus verdict history as a single reasoning unit.

In a world where agents generate research faster than humans can
peer-review it, falsifiability has to be enforced at commit time,
not at conference time. MIT licensed, stdlib + pyyaml,
`pip install .` and go.

falsify uses falsify to pre-register claims about falsify — three
locked self-claims (`cli_startup`, `test_coverage_count`,
`claude_surface`) verified on every CI run.

Demo video script lives in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md)
— shot-by-shot, TTS-ready voiceover, SRT captions.

## How Opus 4.7 was used

Opus 4.7's 1M-token context is what made this shape of tool
possible. Each forked-context subagent loads the full verdict
store plus the input text as a single reasoning unit — no paging,
no retrieval indirection. `claim-auditor` performs paraphrase-aware
cross-reference of PR bodies and release notes against every
`verdict.json`. `verdict-refresher` reads `falsify stats --json`
and autonomously re-runs stale specs. On top, three in-session
skills drive the human-facing workflow: `hypothesis-author` drafts
a falsifiable spec through a five-question dialogue, the `falsify`
skill routes any empirical claim to the right pipeline step, and
`claim-audit` runs a fast regex pass before escalating to the
subagent. Every commit carries a `Co-Authored-By: Claude` trailer.

## Repo link

Placeholder: `https://github.com/<USER>/falsify-hackathon` — replace
before submission.

## Demo video link

Placeholder: `<YouTube or Vimeo URL>` — replace Friday after upload.

## Trust model

We document a serious threat model in
[`docs/ADVERSARIAL.md`](docs/ADVERSARIAL.md) — 8 defended attacks,
6 explicitly undefended. We earn trust by stating limits.
[`docs/COMPARISON.md`](docs/COMPARISON.md) gives a 15-row feature
matrix vs MLflow, W&B, DVC, OSF, pytest, and pre-commit — honest
about where each competitor is stronger.

## License

MIT — new work, not derived from prior projects.

## Tech stack

Python 3.11+, pyyaml only. Stdlib `unittest`. Bash smoke test.
GitHub Actions CI. Claude Code skills and subagents.

## Team

Solo — Cüneyt Öztürk (Studio 11, Istanbul).

## What's next

- MCP server exposing the verdict log across Claude sessions.
- Managed Agents deployment for cloud-based verdict refresh.
- Multi-spec aggregation dashboard.
- Integrations: GitHub PR bot, Slack notifier.

## Submission checklist

- [ ] Repo public on GitHub
- [ ] CI badge green
- [ ] LICENSE file present (MIT)
- [ ] README polished
- [ ] DEMO.md runnable end-to-end
- [ ] Demo video uploaded
- [ ] Submission form filled
- [ ] Form submitted before April 26 8:00 PM EST
