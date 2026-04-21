# JUJU anonymized sample

Public-safe 20-row fixture for demonstrating the Falsification Engine
against a Polymarket-style prediction ledger.

Event IDs are the first 8 hex characters of SHA-256 hashes of
**synthetic** event names — this file is representative, not sourced
from the real ledger. The full JUJU ledger remains private; the
numbers here are seeded so the Brier score lands near 0.22, close
enough to the `0.25` threshold that both PASS and FAIL demos are
credible with a small threshold nudge.

## Running the demo

```bash
mkdir -p .falsify/juju
cp examples/juju_sample/spec.yaml .falsify/juju/spec.yaml
python3 falsify.py lock juju && python3 falsify.py run juju && python3 falsify.py verdict juju
```
