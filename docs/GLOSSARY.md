# Glossary

Short definitions for the concepts and commands you will encounter
in falsify's docs. Terms are ordered alphabetically; cross-references
use the link target `#term-slug`.

## Audit trail

The append-only JSONL stream produced by `falsify export`. Every
lock, run, and verdict writes one line, so the trail reconstructs
the full history of a claim from pre-registration through current
state. It is what makes post-hoc threshold edits visible rather
than plausibly-deniable.
See also: [Lock file](#lock-file), [Verdict](#verdict),
[ADVERSARIAL.md](ADVERSARIAL.md).

## Canonical YAML

The deterministic YAML serialization used as the hash substrate:
`yaml.safe_dump(spec, sort_keys=True, default_flow_style=False,
allow_unicode=True, width=4096)`. Two specs with the same semantic
content produce byte-identical canonical YAML, and therefore the
same [spec hash](#hash-spec-hash).
See also: [Hash (spec hash)](#hash-spec-hash),
[Spec](#spec), [ARCHITECTURE.md](ARCHITECTURE.md).

## Claim

A falsifiable statement about a measurable quantity — a
[threshold](#threshold) compared via a [direction](#direction)
against a number returned by a [metric function](#metric-function)
over a dataset. The unit of pre-registration that falsify locks,
runs, and verdicts.
See also: [Spec](#spec), [Failure criteria](#failure-criteria),
[TUTORIAL.md](../TUTORIAL.md).

## Claim contract

The triple `(claim, failure_criteria, experiment)` as it exists at
lock time. It is the "contract" in the sense that changing any of
its parts changes the [spec hash](#hash-spec-hash) and therefore
invalidates the lock — which is the point.
See also: [Hash mismatch](#hash-mismatch),
[Honest relock](#honest-relock),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Direction

One of `above`, `below`, or `equals`. Governs the comparison of a
metric value against the threshold and is strict: `above` means
strictly greater-than, `below` means strictly less-than. The
strict semantic is documented in the schema comments so that
boundary cases (value exactly equal to threshold) are always
unambiguous.
See also: [Failure criteria](#failure-criteria),
[Threshold](#threshold),
[hypothesis.schema.yaml](../hypothesis.schema.yaml).

## Dogfood

The practice of running falsify against claims about its own
behaviour. The three shipped self-claims (`cli_startup`,
`test_coverage_count`, `claude_surface`) are re-verified by
`make dogfood` on every CI run. The shorthand makes the loop
visible: if falsify breaks its own contract, you see it first.
See also: [Self-claim](#self-claim),
[Self-dogfooding](#self-dogfooding),
[CLAUDE.md](../CLAUDE.md).

## Exit code

A deterministic integer signal emitted by every falsify
subcommand. Fixed semantics: `0` PASS, `2` bad spec or
INCONCLUSIVE, `3` [hash mismatch](#hash-mismatch), `10` FAIL,
`11` [guard](#audit-trail) violation. Treated as API — exit
codes never change without a major version bump.
See also: [Verdict](#verdict), [Replay](#replay),
[README.md](../README.md).

## Failure criteria

The falsification block of a spec: metric, direction, and
threshold, plus a minimum sample size. A run PASSes when the
observed metric on the required sample survives the criterion,
FAILs when it does not, and goes
[INCONCLUSIVE](#inconclusive) when the sample is too small.
See also: [Claim](#claim), [Threshold](#threshold),
[Direction](#direction).

## Falsification

The Popper sense: a claim is meaningful only if it is testable
and could fail. falsify the tool encodes this as a workflow —
the spec names the condition under which the claim would die,
and the verdict records whether that condition held.
See also: [Claim](#claim), [Pre-registration](#pre-registration),
[FAQ.md](FAQ.md).

## Hash (spec hash)

A SHA-256 digest of the [canonical YAML](#canonical-yaml) bytes
of a spec. Identifies a locked claim uniquely and detects any
post-lock edit. Stored in `spec.lock.json` under `spec_hash`; 64
lowercase hex characters.
See also: [Canonical YAML](#canonical-yaml),
[Lock file](#lock-file),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Hash mismatch

The exit-3 condition when the stored `spec_hash` in
`spec.lock.json` disagrees with a freshly-computed hash of the
current spec. `falsify run` refuses to execute until the
operator resolves the divergence with an [honest
relock](#honest-relock) or by reverting the edit.
See also: [Hash (spec hash)](#hash-spec-hash),
[STALE](#stale), [ADVERSARIAL.md](ADVERSARIAL.md).

## Honest relock

Explicitly running `falsify lock <name> --force` after an
intentional edit to a spec. Produces a new hash and an entry in
the [audit trail](#audit-trail), so the change is never silent.
See also: [Hash mismatch](#hash-mismatch),
[Pre-registration](#pre-registration),
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Hypothesis

The author-facing name for a spec draft — used by the
`hypothesis-author` skill and in `hypothesis.schema.yaml`. Once
a hypothesis is locked it becomes a claim in the CLI vocabulary;
the terms are otherwise interchangeable.
See also: [Claim](#claim), [Spec](#spec),
[hypothesis.schema.yaml](../hypothesis.schema.yaml).

## INCONCLUSIVE

A [verdict](#verdict) state where a run executed but the sample
size fell below `minimum_sample_size`. Not a PASS, not a FAIL —
the run simply did not have enough data to decide. Exit code
`2`.
See also: [Minimum sample size](#minimum-sample-size),
[Verdict](#verdict),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Lock file

`spec.lock.json`, the small JSON artefact written by
`falsify lock`. Stores the [spec hash](#hash-spec-hash), the
`locked_at` timestamp, and the canonical YAML bytes that were
hashed. Tracked in git so the lock is part of the claim's
history.
See also: [Audit trail](#audit-trail), [Spec](#spec),
[TUTORIAL.md](../TUTORIAL.md).

## MCP (Model Context Protocol)

The stdio protocol that exposes falsify verdicts to Claude
Desktop and Claude Code sessions via `mcp_server/`. Ships four
tools (`list_verdicts`, `get_verdict`, `get_stats`,
`check_claim`) and three resource URIs. Optional install:
`pip install -e '.[mcp]'`.
See also: [Verdict](#verdict),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Metric function

A Python callable referenced by `experiment.metric_fn` in the
form `module:function`. Must return a `(value, sample_size)`
pair. Runs in the same process as `falsify run`; the metric
module is imported from the current working directory.
See also: [Spec](#spec), [Failure criteria](#failure-criteria),
[EXAMPLES.md](EXAMPLES.md).

## Minimum sample size

`falsification.minimum_sample_size` in the spec. A floor below
which a run is recorded as [INCONCLUSIVE](#inconclusive) rather
than PASS or FAIL — the machinery refuses to decide on
underpowered data.
See also: [INCONCLUSIVE](#inconclusive),
[Failure criteria](#failure-criteria).

## Pre-registration

Locking a claim before running the experiment. The single most
important discipline in falsify: the [hash](#hash-spec-hash)
published at lock time is what proves the claim did not move to
fit the data.
See also: [Prime Directive](#prime-directive),
[Hash (spec hash)](#hash-spec-hash),
[ADVERSARIAL.md](ADVERSARIAL.md).

## Prime Directive

The three-line rule stated in `CLAUDE.md`: every claim is locked
before it is run; hash mismatches are never silenced; threshold
edits require an explicit relock and a visible audit entry.
See also: [Pre-registration](#pre-registration),
[Honest relock](#honest-relock), [CLAUDE.md](../CLAUDE.md).

## Replay

Re-executing a stored run's metric function against its recorded
dataset, via `falsify replay <run_id>`. Exits `0` if the replay
reproduces the stored value within tolerance, `10` otherwise —
the standard reproducibility test.
See also: [Verdict](#verdict), [Exit code](#exit-code),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Self-claim

A [claim](#claim) about falsify itself, sourced under
`claims/self/` and locked under `.falsify/`. The shipped set is
`cli_startup`, `test_coverage_count`, and `claude_surface`.
See also: [Dogfood](#dogfood),
[Self-dogfooding](#self-dogfooding), [CLAUDE.md](../CLAUDE.md).

## Self-dogfooding

See [Dogfood](#dogfood). The longer name is the one used in
CI logs and release-check Gate 12; it means the same thing.
See also: [Dogfood](#dogfood), [Self-claim](#self-claim).

## Skill

A Claude Code capability described in
`.claude/skills/<name>/SKILL.md`. falsify ships five
(`hypothesis-author`, `falsify`, `claim-audit`, `claim-review`,
`falsify-ci-doctor`). Skills run in the main session; heavier
work routes to [subagents](#subagent).
See also: [Slash command](#slash-command), [Subagent](#subagent),
[ARCHITECTURE.md](ARCHITECTURE.md).

## Slash command

A Claude Code prompt defined in `.claude/commands/<name>.md`.
falsify ships three (`/new-claim`, `/audit-claims`,
`/ship-verdict`). Commands compose skills and CLI calls into a
single-keystroke workflow.
See also: [Skill](#skill), [Subagent](#subagent),
[README.md](../README.md).

## Spec

The YAML file declaring a claim, its [failure
criteria](#failure-criteria), and its experiment reference. The
canonical bytes of this file are what gets hashed at lock time.
See also: [Claim](#claim), [Canonical YAML](#canonical-yaml),
[hypothesis.schema.yaml](../hypothesis.schema.yaml).

## STALE

A [verdict](#verdict) state where a run exists but its
`spec_hash` no longer matches the current canonical hash — i.e.,
the spec has changed since the last run. Neither PASS nor FAIL;
the run is simply out-of-date.
See also: [Hash mismatch](#hash-mismatch), [Verdict](#verdict),
[ADVERSARIAL.md](ADVERSARIAL.md).

## Subagent

A Claude Code agent described in `.claude/agents/<name>.md`,
forked-context by default. falsify ships two: `claim-auditor`
(semantic PR cross-reference) and `verdict-refresher`
(autonomous re-runs of STALE specs).
See also: [Skill](#skill), [Slash command](#slash-command),
[MANAGED_AGENTS.md](MANAGED_AGENTS.md).

## Threshold

The numeric cutoff inside a [failure criteria](#failure-criteria)
block. Compared against the metric value via the chosen
[direction](#direction). Changing it silently is the
canonical dishonesty pattern falsify is built to surface.
See also: [Direction](#direction),
[Failure criteria](#failure-criteria),
[Honest relock](#honest-relock).

## UNLOCKED

A state where a `spec.yaml` exists but has no `spec.lock.json`
beside it. `falsify run` refuses to execute an UNLOCKED spec —
that would violate [pre-registration](#pre-registration).
See also: [Pre-registration](#pre-registration),
[Lock file](#lock-file), [Verdict](#verdict).

## UNRUN

A state where a spec is locked but has never been executed.
Seen immediately after `falsify lock` on a fresh claim. The
corresponding exit code depends on the subcommand; `falsify
why <claim>` reports `state: UNRUN`.
See also: [Verdict](#verdict),
[Pre-registration](#pre-registration),
[TUTORIAL.md](../TUTORIAL.md).

## Verdict

The recorded outcome of a run: one of PASS, FAIL,
[INCONCLUSIVE](#inconclusive), [STALE](#stale),
[UNRUN](#unrun), [UNLOCKED](#unlocked), or UNKNOWN. Stored in
`verdict.json` beside the run it describes; the value reported
by `falsify verdict` and by the MCP `get_verdict` tool.
See also: [Exit code](#exit-code), [Audit trail](#audit-trail),
[ARCHITECTURE.md](ARCHITECTURE.md).
