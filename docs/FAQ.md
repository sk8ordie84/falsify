# FAQ — "Why not just X?"

Direct answers to the objections any serious reader raises within
five minutes of discovering falsify. No marketing voice. Where a
competitor is better at something, we say so.

For a scannable feature matrix, see [COMPARISON.md](COMPARISON.md).

## Why not just use git hooks?

Git hooks catch syntactic drift — trailing whitespace, lint errors,
formatting. Falsify catches *semantic* drift — a threshold getting
lowered, a metric being swapped, a direction getting flipped. Those
are invisible to any lint hook because the YAML is still
well-formed.

We ship a `commit-msg` guard precisely because hooks and falsify
compose — the guard reads `verdict.json` and blocks commits that
affirmatively reference a FAIL verdict. Install it with:

    falsify hook install

## Why not OSF / AsPredicted.org?

OSF Registries and AsPredicted are excellent for *academic*
pre-registration with human reviewers and a publication lifecycle.
Falsify is for *CI-gated, machine-verifiable* claims inside a
team's repo — a verdict every PR, not a preregistration every
paper.

They are complementary. Export to OSF when you publish a result;
run falsify on every PR that touches a claim. Different cadences,
same discipline.

## Why not MLflow / Weights & Biases / Neptune?

Those tools track metric *values* across runs. They are excellent
at it — MLflow's lineage graph is richer than ours will ever be;
W&B's visualization and dashboarding beat our ASCII sparkline by a
wide margin.

Falsify answers a different question: was the claim *contract* —
threshold, direction, dataset, metric function — fixed *before*
any run? That question is not what experiment trackers exist to
answer. Pipe your MLflow run IDs into `metric_fn` and use both.

## Why not DVC / Pachyderm for data versioning?

Falsify hashes the spec, not the data. We assume your dataset path
is pinned and content-addressed — which is exactly what DVC and
Pachyderm do well. Our `experiment.command` can invoke `dvc pull`
before the metric runs.

Short version: DVC answers "which bytes did I compute over?";
falsify answers "which claim did I commit to before computing?"
Use both.

## Why not just pytest with assertions?

Pytest asserts in CI *after* the claim is known. If the threshold
in `assert accuracy > 0.85` gets nudged to `0.80` in the same PR
that adds the test, no hook catches it — the test still passes.

Falsify locks the claim *before* the data is seen. A test suite
whose thresholds are silently edited alongside the data is not a
test suite; it is confirmation bias with green checkmarks. Run
falsify *next to* pytest, not instead of it.

## Isn't this overkill for ML experiments?

For a solo Kaggle notebook, yes — skip it. For a team shipping AI
features to production, no. Silent threshold lowering is the #1
failure mode of internal ML teams we have talked to: not malice,
just pressure.

One `falsify lock` takes three seconds. One undetected regression
that ships because the bar quietly moved costs weeks of recovery.
The math favors the lock.

## Why stdlib + pyyaml? Why not Pydantic / attrs?

Zero runtime dependency surface on the hash path means zero
supply-chain risk on the invariant that matters most. `pyyaml` is
load-bearing for canonical serialization, pinned, and widely
audited.

Everything else is stdlib on purpose. A poisoned Pydantic release
could silently break canonicalization; we prefer a smaller attack
surface to a prettier type decorator. See
[`ADVERSARIAL.md`](ADVERSARIAL.md) "Supply-chain compromise".

## How do you handle stochastic metrics (e.g., LLM output drift)?

Three tactics, in order of preference.

1. Seed the metric. Any function that accepts `random_state`
   should receive one; make it part of the spec so it hashes.
2. Use `falsify replay --tolerance 1e-9` (or looser) to allow
   bounded numerical drift between record and replay.
3. For unavoidable LLM variance, don't claim raw outputs — claim
   an agreement rate against a calibrated judge. The `llm-judge`
   template in `falsify init --template llm-judge` demonstrates.

Raw LLM output equality is not a claim; agreement *rate* is.

## What prevents me from just deleting .falsify/?

Nothing at the filesystem layer. Falsify is a discipline tool,
not a zero-trust system — a determined adversary with `rm -rf`
will win.

The answer is git. Commit `.falsify/*/spec.yaml`,
`spec.lock.json`, and `verdict.json` (only `runs/` is
`.gitignore`d). The audit trail is only as durable as version
control — which, for an engineering team, is plenty.

## Is the SHA-256 hash overkill?

No. SHA-256 costs under a millisecond on any spec a human would
write, and its collision resistance (~2^128 chosen-target work)
puts tampering outside any realistic adversary's budget.

A weaker hash would buy nothing and cost future-proofing. The
formal threat model is in [`ADVERSARIAL.md`](ADVERSARIAL.md)
"Hash collision".

## Why not put all this in one YAML schema + a GitHub Action?

The schema alone doesn't gate runs — YAML validators are happy
with any well-formed file. The Action alone doesn't give you
`falsify why`, `falsify trend`, or the local `commit-msg` guard
that fires before CI even sees the commit.

The CLI is the primary surface. The schema and the shipped
`.github/workflows/falsify.yml` are derivatives that fall out of
it — not substitutes for it.

## What about Bayesian stopping rules?

Planned for 0.3.0. See [ROADMAP.md](../ROADMAP.md). Current
stopping-rule support is fixed-`n` plus manual review, which is
adequate for pre-registration discipline: a sample size is
declared in the spec, hashed with the rest, and cannot drift
post-hoc.

Sequential and Bayesian rules add power but also add a larger
specification surface; we chose to ship the fixed-`n` case
cleanly before generalizing.

## Can I use this for non-ML claims (e.g., API latency, p99 error rate)?

Yes. The `latency` template demonstrates — a `(p99_ms, n_requests)`
tuple against a `direction: below` threshold. Any function
returning `(float, int)` is a valid `metric_fn`.

Falsify is agnostic to domain. Accuracy, latency, calibration
(Brier), agreement rate, AB-test delta, error-budget burn — all
the same pipeline. See [`EXAMPLES.md`](EXAMPLES.md) for five
worked claim types.

## Why the unfriendly exit codes (0, 2, 3, 10, 11)?

They *are* the API. CI gating wants deterministic integer
discrimination: exit 10 means "locked claim failed, block the
merge"; exit 3 means "spec was tampered with since lock"; exit
11 means "commit message contradicts a FAIL verdict".

A shell one-liner can act on those without parsing JSON, which is
the point. See [`CLAUDE.md`](../CLAUDE.md) Prime Directive and
[`ARCHITECTURE.md`](ARCHITECTURE.md) "Why exit codes, not
JSON-only output".

## What if I'm wrong about my threshold?

Edit the spec, relock, re-run. That is the honest path:

    # change threshold in .falsify/<name>/spec.yaml
    falsify lock <name> --force
    falsify run <name>
    falsify verdict <name>

The `--force` re-lock produces a new hash and a visible audit
entry; `falsify export` records it. The dishonest path — edit
the spec without relocking — is blocked at `run` time by exit 3
(hash mismatch) and surfaced as `STALE` by `falsify why`.

Being wrong is cheap. Hiding that you were wrong is the expensive
part, and that is what the hash chain prices in.
