# falsify — Git for AI honesty

> Lock the claim before the data, or it didn't happen.

## Category

Developer Tools / AI Infrastructure — Anthropic "Built with Opus
4.7" hackathon, April 21–26 2026.

## The problem

AI teams ship claims — "our model hits 92% accuracy", "p95
latency is under 200ms", "hallucination rate is below 3%" — and
then silently edit the threshold when the claim stops holding.
There is no Git-native enforcement of pre-registration for
machine-checkable claims. Silent threshold lowering is the #1
failure mode of internal ML teams we have talked to: not malice,
just pressure. By the time anyone notices, the commit history
looks clean and the bar has quietly moved.

## What falsify does

falsify is a CLI that pre-registers each claim in a hash-locked
YAML spec before the experiment runs. Threshold, direction,
dataset path, and metric-function reference are sealed in
canonical YAML and SHA-256 hashed. Any silent edit changes the
hash; any run against a tampered spec exits with code 3. CI
gates on deterministic exit codes (0 PASS, 10 FAIL, 3 hash
mismatch, 11 guard violation). The honest path — explicit
`--force` relock plus a visible audit entry — is fast; the
dishonest path is blocked at run time by the hash mismatch.

## Why it matters for Opus 4.7

Claude Code is already being used to generate and evaluate ML
claims every day. falsify gives Claude — and humans working with
Claude — a shared discipline tool: the model can draft a
falsifiable spec through the `hypothesis-author` skill, a
forked-context subagent can audit every claim against the full
verdict store paraphrase-aware, a slash command can scaffold the
full lock-run-verdict lifecycle, and an MCP server lets every
Claude session query live verdicts across the repo. Opus 4.7's
1M-token context makes each of those moves a single-pass
reasoning operation rather than a retrieval dance. This is what
pre-registration looks like when AI writes the experiments.

## Scope delivered

- 59 commits, 2 days of pair-programming with Claude Opus 4.7.
- 454 tests across 58 files, all passing. 10 intentionally
  skipped (MCP SDK gated + Python 3.11-only pyproject parity).
- 17 CLI subcommands — init, lock, run, verdict, guard, list,
  stats, diff, hook, doctor, version, export, verify, replay,
  why, trend, score.
- 4 Claude skills (`hypothesis-author`, `falsify`, `claim-audit`,
  `claim-review`) plus 2 forked-context subagents
  (`claim-auditor`, `verdict-refresher`).
- 3 Claude Code slash commands (`/new-claim`, `/audit-claims`,
  `/ship-verdict`).
- 1 MCP server with 4 tools (`list_verdicts`, `get_verdict`,
  `get_stats`, `check_claim`) and 3 resource URIs, real
  `mcp.server.Server` SDK wiring with lazy import.
- 2 Managed Agents deployment manifests (scheduled + on-demand).
- 5 claim templates (`accuracy`, `latency`, `brier`,
  `llm-judge`, `ab`) via `falsify init --template`.
- `pre-commit` framework integration — consumer-facing
  `.pre-commit-hooks.yaml` plus local `.pre-commit-config.yaml`.
- Docker reproducible-environment image (`make docker-build`).
- Self-dogfooded: 3 locked claims about falsify's own
  properties (`cli_startup`, `test_coverage_count`,
  `claude_surface`) re-verified on every CI run. Honesty score
  1.00.

## 30-second reproduction

    git clone https://github.com/<USER>/falsify-hackathon
    cd falsify-hackathon
    pip install -e .
    falsify init --template accuracy
    falsify lock accuracy
    falsify run accuracy
    falsify verdict accuracy   # exit 0 = PASS

Replace `<USER>` with the final GitHub handle before submission.

## The money shot

Edit the locked `spec.yaml` to lower the threshold. Run again.
The CLI exits 3 — hash mismatch — and refuses to produce a
verdict against a tampered spec. The lie is blocked
automatically. The honest correction is `falsify lock --force`,
which produces a new hash and a visible audit entry recoverable
via `falsify export`. That single workflow is the difference
between a test suite (asserts after the fact) and a claim
contract (sealed before the fact).

## Demo video

- 90-second video: `<VIDEO_URL>` — replace before submission.
- Script and storyboard:
  [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — shot-by-shot
  timing, TTS-ready voiceover, and SRT captions.

## Documentation depth

- [`README.md`](README.md) — landing page and quickstart.
- [`TUTORIAL.md`](TUTORIAL.md) — 15-minute hands-on walkthrough
  from zero to first locked claim.
- [`DEMO.md`](DEMO.md) — the 5-step live walkthrough used in the
  hackathon demo video.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design,
  data flow, core invariants, commands table.
- [`docs/ADVERSARIAL.md`](docs/ADVERSARIAL.md) — threat model with
  8 defended attacks and 6 explicitly undefended.
- [`docs/FAQ.md`](docs/FAQ.md) — 15 direct answers to
  "why not just X?" objections.
- [`docs/COMPARISON.md`](docs/COMPARISON.md) — 15-row feature
  matrix vs MLflow, W&B, DVC, OSF, pytest, pre-commit.
- [`docs/PR_REVIEW.md`](docs/PR_REVIEW.md) — CI integration for
  the `claim-review` skill.
- [`docs/MANAGED_AGENTS.md`](docs/MANAGED_AGENTS.md) — Anthropic
  Console setup guide for cloud deployment.
- [`CLAUDE.md`](CLAUDE.md) — project instructions for Claude
  Code users, encoding the Prime Directive and dev rules.
- [`ROADMAP.md`](ROADMAP.md) — 0.2.0 (MCP + Managed Agents) and
  beyond.
- [`CHANGELOG.md`](CHANGELOG.md) — Keep-a-Changelog format.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — ground rules, setup,
  release ritual.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Contributor
  Covenant v2.1.

## What falsify is NOT

- Not a metric tracker. Use MLflow, W&B, or Neptune.
- Not a data versioner. Use DVC, Pachyderm, or LakeFS.
- Not a publication platform. Use OSF or AsPredicted.
- Not a test framework. Use pytest or your language's
  equivalent.
- falsify is a discipline tool for claim contracts — it composes
  with every tool above rather than replacing any of them.

## Known gaps

- Bayesian and sequential stopping rules are planned for 0.3.0.
  Current stopping-rule support is fixed-n plus manual review.
  See [`ROADMAP.md`](ROADMAP.md).
- Filesystem-level tampering (`rm -rf .falsify/`) is explicitly
  out of scope. Falsify is a discipline tool, not a zero-trust
  system. See [`docs/ADVERSARIAL.md`](docs/ADVERSARIAL.md).
- Single-file `falsify.py` by design; a plugin architecture for
  custom hashers or canonicalizers is not planned — the SHA-256
  invariant is load-bearing.
- MCP server requires the `mcp` Python SDK; degrades gracefully
  to a clear exit-2 hint when the extra is not installed. Plain
  helpers import without it for unit tests.

## Built with Opus 4.7

Every line of code in this repo was written with Claude Opus 4.7
via Claude Code over 2 days of pair-programming. 59 commits, 454
tests, one-shot composition of a CLI, a forked-context subagent
layer, an MCP server, and a full documentation set. The
development loop itself was a demonstration of what this project
advocates: Claude proposed changes; locks were applied to every
self-claim before any run; CI gated on deterministic verdicts;
regressions were caught before merge. Every commit carries a
`Co-Authored-By: Claude` trailer.

## Team

Solo — Cüneyt Öztürk (Istanbul). GitHub: `<USER>` (replace before
submission).

## License

MIT — new work, not derived from prior projects. See
[`LICENSE`](LICENSE).

## Submission checklist

- [ ] Repo public on GitHub; `<USER>` placeholders replaced.
- [ ] CI badge green on `main`.
- [ ] LICENSE file present (MIT).
- [ ] Demo video uploaded; URL substituted above.
- [ ] Submission form filled and reviewed.
- [ ] Form submitted before April 26 8:00 PM EST.
