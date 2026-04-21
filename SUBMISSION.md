# Submission — Falsification Engine

## Project name

Falsification Engine

## One-line tagline

Pre-registration and CI for AI-agent claims — deterministic PASS or
FAIL, not a story.

## Short description

AI agents make empirical claims all day — *"accuracy is up,"* *"our
filter is better,"* *"the reranker beats baseline"* — but rarely pin
down the threshold, the metric, or the stopping rule before the data
arrives. Every verdict becomes post-hoc rationalization: goalposts
move, samples get chosen, winning explanations kept. Falsification
Engine forces scientific discipline onto that loop. You declare the
claim, lock the spec with a SHA-256 canonical-YAML hash, run the
experiment, and read the exit code. PASS returns 0, FAIL returns
10, a tampered spec returns 3, a guard violation returns 11 —
mechanical, not rhetorical. Inside the repo: eight CLI subcommands
(init, lock, run, verdict, guard, list, stats, diff), a commit-msg
git hook that blocks commits whose messages contradict a locked
verdict, and a GitHub Actions workflow that re-verdicts every push
across Python 3.11 and 3.12. Opus 4.7 contributes three Claude Code
skills (hypothesis-author, the falsify orchestrator, claim-audit)
and two forked-context subagents (claim-auditor for semantic text
cross-reference, verdict-refresher for autonomous stale-verdict
maintenance). In an era of agent-generated research, falsifiability
has to be enforced at commit time, not at peer-review time.

## How Opus 4.7 was used

Three-layer usage. First, Claude Code with Opus 4.7 wrote every
line in this repository — each commit carries a Co-Authored-By
trailer for auditability. Second, three in-session skills
orchestrate the claim-to-verdict workflow: hypothesis-author runs a
five-question dialogue (claim, metric, dataset, threshold/direction,
stopping rule) to draft a falsifiable spec.yaml; the falsify
orchestrator routes any empirical claim to the right step in the
init/lock/run/verdict pipeline; claim-audit scans pasted text for
assertions and cross-references the verdict store. Third, two
forked-context subagents exploit Opus 4.7's 1M-token window:
claim-auditor performs paraphrase-aware semantic audit against
every verdict.json; verdict-refresher reads `stats --json` and
autonomously re-runs stale specs. The long context let us reason
over the whole repo and verdict history as a single unit.

## Repo link

Placeholder: `https://github.com/<USER>/falsify-hackathon` — replace
before submission.

## Demo video link

Placeholder: `<YouTube or Vimeo URL>` — replace Friday after upload.

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
