# Comparison — falsify vs adjacent tools

## Scope

We compare on **claim-contract discipline** — did the team fix
threshold, direction, metric, and dataset before the data was
seen? — not on general-purpose ML-infrastructure features.
Tools like MLflow, W&B, and DVC do things falsify will never do;
falsify does one thing none of them enforce.

## Feature matrix

| Feature | falsify | MLflow | W&B | DVC | OSF | pytest | pre-commit |
|---|---|---|---|---|---|---|---|
| Pre-registers claim BEFORE data seen | yes | no | no | no | yes | no | no |
| Hash-locks spec (threshold + direction + metric_fn + dataset path) | yes | partial | partial | partial | partial | no | no |
| Detects silent threshold edits | yes | no | no | no | partial | no | no |
| Deterministic exit codes as CI gate | yes | partial | partial | partial | no | yes | yes |
| Replays past runs for reproducibility | yes | partial | partial | yes | no | no | no |
| Semantic PR diff review (skill/subagent) | yes | no | no | no | no | no | no |
| Audit trail with chain integrity check | yes | partial | partial | partial | partial | no | no |
| Stdlib + one dep (no heavy runtime) | yes | no | no | no | n/a | yes | partial |
| Domain-agnostic (not ML-specific) | yes | no | no | partial | yes | yes | yes |
| Tracks metric values over time | partial | yes | yes | partial | no | no | no |
| Visualizes metric lineage | partial | yes | yes | partial | no | no | no |
| Data/dataset versioning | no | partial | partial | yes | partial | no | no |
| Academic pre-registration with DOI | no | no | no | no | yes | no | no |
| In-repo test assertion framework | no | no | no | no | no | yes | no |
| Commit-time lint / formatter | partial | no | no | no | no | no | yes |

Cells use plain "yes" / "no" / "partial" so the table stays
grep-friendly. "Partial" means the tool can be coaxed into the
behavior but does not enforce it as a primary contract.

## Positioning paragraphs

### MLflow

Strong on metric tracking, model registry, and run lineage — if
you want to know *what value* a model produced on which commit,
MLflow is the standard answer. Weak on pre-registration
discipline: it logs what happened but doesn't gate *whether
the claim was fixed before it happened*. Complementary, not
competitive: pipe MLflow run IDs into a `metric_fn` and let
falsify gate on the contract while MLflow tracks the history.

### Weights & Biases

Best-in-class visualization and experiment UX; the sweep tools
and charts are genuinely better than anything we will build.
Does not enforce claim contracts: a W&B dashboard will happily
display a chart where the threshold line was silently lowered
between runs. Use W&B for the picture, falsify for the promise.

### DVC

Data-versioning and pipeline reproducibility are load-bearing
for any serious ML repo, and DVC's content-addressed data model
is the right primitive. Falsify pins the *spec* side of the
contract (what counts as success) and assumes DVC or equivalent
pins the *data* side (what counts as input). Run both; one's
hash protects threshold+metric, the other's hash protects bytes.

### OSF / AsPredicted

Gold standard for academic human-reviewed pre-registration, with
DOIs, embargoes, and a publication lifecycle. Slow and manual by
design — the human reviewer is the feature. Falsify is CI-speed
pre-registration for internal repos: every PR, not every paper.
Use OSF when you publish; use falsify on every commit.

### pytest

Asserts after the fact: `assert accuracy > 0.85` runs in CI, and
if the threshold was silently edited to `0.80` in the same PR,
pytest happily passes. Falsify locks the contract before the
data is seen; the two jobs are different. Coexist in the same CI
pipeline without conflict — falsify gates the claim, pytest
gates the code.

### pre-commit

File-level lint and formatting hooks fired on staged files
before commit. Excellent at syntactic hygiene, silent about
semantics. Falsify is a claim-level semantic gate. We ship
[`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) exporting
`falsify-guard`, `falsify-doctor`, and `falsify-stats` so the
two tools compose without friction.

## What falsify is NOT

- **Not a metric store.** Use MLflow, W&B, or Neptune.
- **Not a dataset versioner.** Use DVC, Pachyderm, or LakeFS.
- **Not a publication platform.** Use OSF or AsPredicted.
- **Not a test framework.** Use pytest, unittest, or your
  language's equivalent.
- **Not a linter or formatter.** Use pre-commit, ruff, mypy,
  eslint — whatever your repo already ships.
- **Not a dashboard.** We emit JSON, SVG, shields.io badges, and
  a self-contained HTML page; plug into your dashboard of choice.

## When to reach for falsify

1. **Shipping AI features to production where benchmark
   regressions must gate merges.** You want a CI rule that says
   "if the locked accuracy claim FAILs, the PR cannot merge" and
   you want the threshold in that claim to be immutable after the
   first run.
2. **Team reviews where "trust me, it still passes" is a
   recurring phrase.** The ritual of lock-before-run replaces
   social trust with a hash mismatch that anyone can reproduce
   from the diff alone.
3. **Pre-registering a claim for future audit.** An internal
   engineering claim that you might need to defend to legal,
   compliance, or an external auditor six months from now —
   `falsify export` gives them the JSONL trail, `falsify verify`
   proves the chain is intact.

If none of those match, falsify is probably overkill for your
use case; reach for whichever tool above is the better fit.

## Further reading

- [`docs/FAQ.md`](FAQ.md) — sentence-level objection handler
  (15 direct "why not just X?" answers).
- [`docs/ADVERSARIAL.md`](ADVERSARIAL.md) — threat model and
  attack enumeration.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — internal data flow,
  invariants, and design principles.
- [`ROADMAP.md`](../ROADMAP.md) — what is planned vs explicitly
  out of scope.
