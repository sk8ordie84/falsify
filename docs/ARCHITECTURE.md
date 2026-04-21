# Architecture — Falsification Engine

## One-sentence summary

A deterministic, hash-anchored claim verifier that turns
pre-registration into a CI gate.

## Data flow

    spec.yaml  ──► canonicalize ──► SHA-256 hash ──► spec.lock.json
                                                         │
                                                         ▼
    run command ──► stdout/stderr ──► metric_fn ──► (value, n)
                                                         │
                                                         ▼
              threshold + direction + n ──► verdict.json
                                                         │
            ┌─────────────────────────────────────────────┤
            ▼                                             ▼
    falsify guard (commit-msg)              falsify stats (dashboard)

Every intermediate artifact is a plain text file under
`.falsify/<name>/`. Nothing leaves the directory; every run is
reproducible from what's on disk.

## Core invariants

- **Canonical YAML + SHA-256** → the same logical spec always hashes
  to the same 64 hex characters across machines and OSes.
- **The verdict is a pure function** of `(spec.lock.json, run
  artifacts)` — given the same lock and the same run directory,
  `falsify verdict` returns the same PASS/FAIL and writes byte-
  identical `verdict.json` (modulo the `checked_at` timestamp).
- **The commit-msg guard reads `verdict.json`, never recomputes.**
  Guard decisions are therefore as fresh as the last `run + verdict`
  pair, and no faster — stale verdicts stay stale until a human or
  the `verdict-refresher` subagent re-runs them.
- **Exit codes are the API.** `0` PASS, `10` FAIL, `2`
  INCONCLUSIVE / bad spec, `3` hash mismatch, `11` guard violation.
  Everything else the CLI prints is for humans.

## Module layout

| Module                    | Responsibility                                                         |
|---------------------------|------------------------------------------------------------------------|
| `falsify.py::cmd_init`    | scaffold `.falsify/<name>/` from `examples/template.yaml`              |
| `falsify.py::cmd_lock`    | canonicalize `spec.yaml` → write `spec.lock.json` + SHA-256 hash       |
| `falsify.py::cmd_run`     | subprocess the experiment, capture stdout/stderr + metadata artifact   |
| `falsify.py::cmd_verdict` | import `metric_fn`, apply threshold + direction, write `verdict.json`  |
| `falsify.py::cmd_guard`   | 3-mode: text-match, scan, wrap — exit 11 on contradiction              |
| `falsify.py::cmd_stats`   | aggregate `.falsify/*/verdict.json` into a table or JSON               |
| `falsify.py::cmd_diff`    | unified diff between the locked canonical YAML and the current spec    |
| `falsify.py::cmd_list`    | enumerate spec states with lock hash + last run + verdict              |
| `falsify.py::cmd_hook`    | install / uninstall commit-msg guard with backup                       |
| `falsify.py::cmd_doctor`  | environment + repo + per-spec health check                             |
| `falsify.py::cmd_version` | print version string (also as top-level `--version` flag)              |

## Why SHA-256 of canonical YAML (not of the raw file)

Raw YAML is whitespace-sensitive. Two semantically identical specs
— same keys, same values, different indentation or key order or
comment layout — would hash to different digests, and the lock
would flag trivial editor reformatting as tampering.

`yaml.safe_dump(..., sort_keys=True, default_flow_style=False)`
produces a stable canonical serialization: keys sorted, whitespace
normalized, comments stripped. Any semantic change (threshold,
metric, direction, stopping rule) flips the hash; comment-only
edits and reformatting don't. That's the behavior you want from a
pre-registration primitive — strict on substance, forgiving on
style.

## Why exit codes, not JSON-only output

Unix already has a composition story for yes/no verdicts: exit
codes. They slot into git hooks (`exec falsify guard "$MSG"`), CI
workflows (`run: python3 falsify.py verdict foo`), `make` targets,
and shell `&&` chains without any parsing. The shape of every
integration — "if the claim failed, stop the build" — becomes a
one-liner. JSON output is available where it helps (`list --json`,
`stats --json`, `verdict.json`) but it's a bonus, not the primary
interface. You can use this tool from a `sh` script that never
imports a YAML parser.

## Why forked context for subagents

Both subagents (`claim-auditor` and `verdict-refresher`) load the
full verdict store plus their input text or target spec set. That's
potentially tens of kilobytes of structured context per invocation.
Running them in a forked context means they don't pollute the
parent Claude Code session: the parent's token budget stays clean,
prior reasoning stays intact, and the subagent returns only a
structured report. Opus 4.7's 1M-token window lets each subagent
reason over the entire repo and verdict history as a single unit
without paging.

## Extension points

- MCP server exposing `verdict.json` as a Claude-tool resource so
  verdicts are queryable across sessions and other Claude surfaces.
- Managed Agents cloud deployment for scheduled verdict refresh
  (replaces manually invoking `verdict-refresher`).
- Git `pre-push` hook alongside the existing `commit-msg` hook —
  block a push when any claim is FAIL or STALE, not just commits
  whose messages contradict a verdict.
- Multi-metric specs (e.g. accuracy AND latency) — the current
  schema allows multiple `failure_criteria` entries; verdict logic
  just needs to thread multiple values through `metric_fn`.
- Remote artifact storage (S3 or equivalent) for reproducible
  re-runs of expensive experiments across machines.
- More claim types (see [docs/EXAMPLES.md](EXAMPLES.md) for
  accuracy / latency / calibration / agreement / AB).

The full post-hackathon plan lives in [ROADMAP.md](../ROADMAP.md).

## What this is NOT

- **Not a statistical test framework.** We don't compute p-values,
  confidence intervals, or effect sizes. The spec author declares
  the threshold; Falsification Engine just checks observation
  against it deterministically.
- **Not an experiment runner.** We shell out to whatever
  `experiment.command` the spec names. Orchestration, scheduling,
  and resource allocation stay outside scope.
- **Not a replacement for peer review.** It's a tripwire, not a
  court. A PASS verdict says "the claim survived its own
  pre-registered falsification attempt", not "the claim is true".

## Design principles

1. **Determinism over flexibility.** Same inputs → same hash, same
   verdict, same exit code, every time.
2. **Exit codes are the contract.** Anything that breaks the exit
   code table is a breaking change.
3. **Stdlib + one dep (`pyyaml`).** No framework dependencies, no
   test runners beyond `unittest`, no compiled extensions.
4. **Human-readable artifacts.** Specs and verdicts are YAML and
   JSON. Runs are plain stdout/stderr files. No binary blobs.
5. **Every verdict is auditable from a single
   `.falsify/<name>/` directory.** A future reviewer with just that
   directory and the CLI can reproduce the PASS/FAIL decision.
6. **Installable as a package** (`pip install .`) with a `falsify`
   console entry point, not just a script.
