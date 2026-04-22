# Adversarial analysis

A plain-spoken threat model for Falsification Engine. Falsify is a
discipline tool, not a zero-trust system; the point of this
document is to state that explicitly, enumerate the attacks the
tool actually catches, and name the ones it does not.

## Threat model scope

We defend against *claim-level dishonesty*: a researcher, engineer,
or AI agent quietly changing what "success" means between the moment
a claim was written and the moment the data came back. This covers
the realistic failure modes of a single team using falsify in good
faith — the goalposts drift, a threshold gets nudged, a dataset
swap goes unnoticed. Our invariants (canonical YAML hashing,
pre-registered lock, deterministic replay, audit-chain export +
verify) are calibrated for that threat.

We do not defend against adversarial users with filesystem write
access outside the git-tracked surface, supply-chain compromise of
the tool's own dependencies, or collusion between signers. Falsify
raises the cost of dishonesty; it does not make dishonesty
cryptographically impossible. Anyone promising the latter is
selling something.

## Attacks defended

a. **Silent threshold lowering** — editing `threshold` in a locked
   spec post-hoc without re-locking. Example:

       # spec was locked at threshold: 0.85
       sed -i 's/threshold: 0.85/threshold: 0.80/' .falsify/claim/spec.yaml
       falsify run claim

   Mitigation: canonical-YAML hash mismatch is caught by `run`
   (exit 3, `EXIT_HASH_MISMATCH`) and surfaced as `STALE` by
   `falsify why`. The `claim-review` Claude skill flags it on PR.

b. **Dataset swap** — running the locked spec against a different
   dataset to cherry-pick a passing number. Example:

       # locked run computed metric over data.csv; attacker points
       # metric_fn at a different file via a side-effectful import
       cp nice-numbers.csv examples/claim/data.csv
       falsify run claim  # now produces a different value

   Mitigation: `falsify replay <run-id>` re-executes the metric
   and asserts the observed value matches the stored value bit-for-bit
   (exit 10 on divergence, configurable `--tolerance`). The audit
   trail exported by `falsify export` records the observed value
   per run, so a post-hoc swap is visible in `diff`.

c. **Direction flip** — changing `direction: above` to
   `direction: below` to invert PASS/FAIL semantics. Example:

       # "accuracy above 0.85" becomes "accuracy below 0.85"
       # so a low observed value now "passes"
       sed -i 's/direction: above/direction: below/' spec.yaml

   Mitigation: the direction field is part of the canonical YAML
   and is hashed. Any change produces a new hash; the locked run
   refuses to proceed. Exit 3 on `run`; `STALE` on `why`.

d. **Metric-function rebind** — swapping `metric_fn: module:strict`
   to `metric_fn: module:lenient` without touching anything else.
   Example:

       # strict counts only high-confidence correct matches;
       # lenient counts partial-credit matches. Same spec text,
       # different answer.
       sed -i 's/metric:strict/metric:lenient/' spec.yaml

   Mitigation: `metric_fn` is part of the spec and contributes to
   the canonical-YAML hash. Hash mismatch → exit 3.

e. **Stale verdict masquerade** — presenting an old PASS verdict
   from a previous spec hash as the current verdict. Example:

       # show an auditor an old verdict.json whose observed value
       # passes, while the current spec has been edited
       cat .falsify/claim/verdict.json  # "verdict": "PASS"
       # ...but spec.yaml was edited since that verdict was written

   Mitigation: each verdict record carries the `spec_hash` it was
   computed under. `falsify why` compares it to the current
   canonical hash and surfaces `STALE` when they diverge. CI gates
   on a fresh `falsify run`; `falsify verify` rejects any exported
   JSONL where a verdict's `locked_hash` doesn't match a preceding
   lock in the chain.

f. **Audit-trail tampering** — editing `.falsify/*/runs/*.json`
   by hand to rewrite a FAIL into a PASS. Example:

       jq '.verdict = "PASS"' verdict.json > patched.json
       mv patched.json verdict.json

   Mitigation: `falsify verify audit.jsonl` walks the exported
   JSONL in order, checks each verdict's `locked_hash` against the
   preceding lock's `canonical_hash`, and fails (exit 10) on any
   break. Repeated tampering without access to the underlying
   `spec.lock.json` canonical YAML breaks the chain.

g. **Unregistered claim** — sneaking a new claim into a PR without
   a matching `spec.lock.json`. Example:

       git add claims/new_thing/spec.yaml
       # no accompanying .falsify/new_thing/spec.lock.json

   Mitigation: the `claim-review` Claude skill inspects the PR
   diff and emits a CRITICAL finding for any spec added without a
   lock. The CI workflow in `.github/workflows/falsify.yml` runs
   `falsify doctor --specs-only` which flags the same condition.

h. **Hash collision** — finding a second spec whose canonical YAML
   hashes to the same SHA-256 as an existing lock. Mitigation:
   treated as out of scope economically. SHA-256 collision
   resistance (~2^128 expected work for a chosen-target collision)
   puts this attack outside any hackathon- or enterprise-scale
   adversary's budget. If SHA-256 is broken in the future, the
   canonical-YAML function remains the same and falsify can migrate
   to SHA-3 with a version bump and a forced re-lock.

## Attacks NOT defended

a. **Adversarial metric function author** — if the person who
   wrote `metric_fn` is lying (e.g., returns a constant 0.9
   regardless of input), falsify cannot detect it. The tool
   assumes the metric is honest code. Mitigation: human review of
   the metric module, and the `claim-review` skill at PR time.

b. **Filesystem-level tampering** — `rm -rf .falsify/` destroys
   every lock, run, and verdict on that machine. Mitigation:
   commit `.falsify/*/spec.yaml`, `spec.lock.json`, and
   `verdict.json` to git (as intended — only `runs/` subdirs are
   in `.gitignore`). Version control is the backup; git history
   is the audit log.

c. **Supply-chain compromise** — a poisoned `pyyaml` release could
   make `safe_dump` return arbitrary bytes, silently breaking
   canonicalization. A poisoned Python interpreter could lie about
   `hashlib.sha256`. Mitigation: pin dependencies in
   `pyproject.toml`, use lockfiles, consume from trusted mirrors;
   this is a SLSA / reproducible-builds problem, not a falsify
   problem.

d. **Collusion** — two signers who both want to lower a threshold
   can coordinate: edit the spec, re-lock, push a PR, approve each
   other's code review. Mitigation: out of scope for a CLI. The
   `claim-audit` subagent can flag affirmative language in commit
   messages that contradicts the old verdict, which raises the
   visibility cost of collusion, but cannot prevent it. This is a
   social-norm problem.

e. **Clock manipulation** — faking `locked_at` or `checked_at`
   timestamps to order events favourably. Mitigation: falsify
   chains events by `spec_hash`, not by wall-clock time. A verdict
   with a too-old or too-new timestamp is still bound to its
   originating lock hash. Stale-verdict detection in `why` uses
   hash mismatch as primary signal; the 7-day clock-based STALE
   rule in `stats` is secondary and advisory.

f. **Denial of service** — locking thousands of trivially-passing
   claims to drown out meaningful ones. Mitigation: `falsify
   score` weights every claim equally, so filler claims dilute
   the honesty score exactly as much as they inflate it.
   `falsify stats` surfaces the population of claims for a human
   reviewer to audit.

## Invariants relied upon

For the design reasoning behind each invariant, see
[`ARCHITECTURE.md`](ARCHITECTURE.md).

- **Canonical YAML serialization** — `yaml.safe_dump(sort_keys=True,
  default_flow_style=False)` produces a stable byte sequence for
  any equivalent spec. Rearrangement and comments do not change
  the hash; substantive edits do.
- **SHA-256 hash over canonical YAML** — binds the spec's bytes
  to a 64-hex-char identifier whose preimage and collision
  resistance are well-understood.
- **Deterministic replay** — `falsify replay` re-executes the
  metric against the stored run directory and asserts the
  observed value matches the stored value (exact or within
  `--tolerance`).
- **Audit-chain integrity** — exported JSONL records every lock,
  run, and verdict in order; `falsify verify` walks the chain
  and rejects any break.
- **Pre-registration ordering** — `lock` must precede `run`. The
  CLI refuses to produce a verdict from an unlocked spec.

## Residual risks and accepted trade-offs

Falsify makes dishonesty expensive, visible, and effortful. It does
not make it impossible. A determined adversary with shell access,
code-review authority, and collaborator buy-in can fabricate a
history. The honest claim of this project is narrower: every class
of fabrication leaves a fingerprint — a new hash, a broken chain,
a flagged PR — that a reviewer who is looking will find.

If you need provably tamper-evident records signed to an external
authority, what you want is a Merkle log anchored to a
timestamping service (or a blockchain, if you insist). Falsify
composes cleanly with those systems — `falsify export` gives you
the data stream — but does not ship one today.

## Reporting vulnerabilities

See [`.github/SECURITY.md`](../.github/SECURITY.md) for the
responsible-disclosure process. Bugs in the invariants listed above
(hash mismatch not caught, replay divergence not flagged, verify
accepting a broken chain) qualify as security issues; please
disclose privately.

## Further reading

- Pre-registration practice: OSF Registries
  (<https://osf.io/registries/>) and AsPredicted
  (<https://aspredicted.org>).
- The reproducibility crisis in empirical research: Ioannidis,
  "Why Most Published Research Findings Are False" (PLoS Medicine,
  2005); Open Science Collaboration, "Estimating the reproducibility
  of psychological science" (Science, 2015).
- Supply-chain security framing: SLSA (<https://slsa.dev/>).
- Reproducible builds: Reproducible Builds project
  (<https://reproducible-builds.org/>).
