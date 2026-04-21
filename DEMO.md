# Falsification Engine — 3-Minute Demo

## Hands-off option

Run `./demo.sh` for an auto-narrated walkthrough that runs the full
PASS → tamper → FAIL → guard-block story end-to-end and restores the
fixture when it's done. Everything below is the manual version if
you want to pace the demo yourself.

## What you'll see

Pre-registration + CI for AI-agent claims: lock a hypothesis, run the
experiment, get a deterministic PASS/FAIL verdict, and let `guard`
block any later text that contradicts the result.

## Prerequisites

- Python 3.11+
- `pip install pyyaml` (inside a venv if your system blocks global pip)
- Clone this repo, `cd` into it.

## Step 1 — Lock a hypothesis (JUJU sample)

```bash
mkdir -p .falsify/juju
cp examples/juju_sample/spec.yaml .falsify/juju/spec.yaml
python3 falsify.py lock juju
```

Expected:

```
✓ Locked juju @ 97c1b9bc4a8c
  claim: brier_score below 0.25
```

The spec's canonical YAML is SHA-256 hashed and stored in
`.falsify/juju/spec.lock.json`. Any semantic edit to `spec.yaml`
after this invalidates the lock and blocks `run` with exit 3.

## Step 2 — Run the experiment

```bash
python3 falsify.py run juju
```

Expected:

```
✓ Run 20260421T184500_000000Z (0.05s)
```

`experiment.command` executed with a 5-minute timeout; stdout, stderr,
a copy of the lock, and a metadata file (host, python version,
duration, return code) are written under
`.falsify/juju/runs/<timestamp>/`. The run is reproducible from those
artifacts alone.

## Step 3 — Get the verdict

```bash
python3 falsify.py verdict juju
```

Expected:

```
Verdict: PASS
  observed brier_score = 0.214265
  threshold: below 0.25
```

The `metric_fn` (`examples.juju_sample.metric:brier_score`) was
imported and checked against the locked criterion. PASS → exit 0,
FAIL → exit 10. `verdict.json` is written so downstream tools
(`list`, `guard`, the `claim-auditor` subagent) can read it without
re-running the experiment.

## Step 4 — Dashboard (list)

```bash
python3 falsify.py list
```

Expected:

```
NAME  LOCKED        LAST RUN                 VERDICT  OBSERVED
juju  97c1b9bc4a8c  20260421T184500_000000Z  PASS     0.214265
```

For CI or scripts, `python3 falsify.py list --json` emits the same
data as a JSON array.

## Step 5 — Guard (CI) and the commit-msg hook

```bash
# Scan mode: non-zero if any claim is FAIL or STALE (> spec drift).
python3 falsify.py guard

# Text mode: block affirmative language that contradicts a logged verdict.
python3 falsify.py guard "we've proven the JUJU ledger is well-calibrated"
```

Because the JUJU verdict is PASS, the text call exits 0 — the
affirmative language matches a *passing* claim. If the latest verdict
had been FAIL or INCONCLUSIVE, the same sentence would have exited
11 with a `BLOCKED:` breakdown on stderr.

Install the hook so every commit gets the same check automatically:

```bash
python3 falsify.py hook install
```

Installs the commit-msg guard; backs up any pre-existing hook.
Now a commit message that asserts a falsified claim is rejected
before it enters history — the same mechanism CI uses on every push.

## Bonus — health check

```bash
python3 falsify.py doctor
```

End-to-end diagnostic — what's OK, what needs attention.

## Bonus — detect a tampered spec

```bash
sed -i 's/threshold: 0.25/threshold: 0.20/' .falsify/juju/spec.yaml
python3 falsify.py diff juju
```

diff proves the spec was tampered with — you see exactly what changed
before re-locking. Exit 3 on any drift; `--force` required to relock.

## Bonus — see all verdicts at once

```bash
python3 falsify.py stats
python3 falsify.py stats --json
python3 falsify.py stats --html > dashboard.html && open dashboard.html
```

One-shot dashboard across every locked spec in `.falsify/` — name,
state, metric, observed value, threshold, sample size, age in days.
Aggregate counts on the last line. The JSON form is CI-friendly;
the `--html` form is a self-contained dark-mode-aware page for
demos and quick browser review (no external assets).

## Bonus — audit trail

```bash
python3 falsify.py export > audit.jsonl
wc -l audit.jsonl
```

One JSON line per event (lock / verdict; add `--include-runs` for
run records too). Append-only. Deterministic — same `.falsify/`
contents produce byte-identical output. Share with a peer to
reproduce your verdicts from nothing but this file plus the
original `spec.yaml`.

## Bonus — verify a peer's audit trail

```bash
python3 falsify.py verify audit.jsonl
```

Walks the JSONL and checks that each verdict's `locked_hash` chains
back to a preceding lock's `canonical_hash`, that timestamps are
monotonic per spec, and that no records were reordered. If anyone
tampered with the file after export, the hash chain breaks and
verify refuses it with exit 10.

---

## See also

- `tests/smoke_test.sh` — full pipeline in one bash driver.
- `.github/workflows/falsify.yml` — unittest + smoke + JUJU e2e in CI.
- `.claude/skills/` — `falsify` (orchestrator), `hypothesis-author`
  (NL → locked spec), `claim-audit` (fast text audit + subagent).
- `.claude/agents/claim-auditor.md` — semantic PR/release auditor.
