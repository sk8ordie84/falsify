#!/usr/bin/env bash
# End-to-end smoke test of the Falsification Engine.
#
# Exercises the full init → edit → lock → run → verdict → list pipeline
# inside a throwaway work directory, then asserts the verdict output
# contains "PASS" and every step exited 0.
#
# Override the interpreter with PYTHON=... if /path/to/python differs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FALSIFY="${REPO_ROOT}/falsify.py"

if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    PY="${REPO_ROOT}/.venv/bin/python"
else
    PY="python3"
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

cp "${REPO_ROOT}/examples/hello_claim/metrics.py" ./metrics.py

echo "--- 1) init ---"
"$PY" "$FALSIFY" init smoke_demo

echo "--- 2) edit spec (fill in placeholders) ---"
cat > .falsify/smoke_demo/spec.yaml <<'YAML'
claim: "Echo script reports a number strictly above 0.5."
falsification:
  failure_criteria:
    - metric: accuracy
      direction: above
      threshold: 0.5
  minimum_sample_size: 1
  stopping_rule: "single echo invocation"
experiment:
  command: "echo 0.80"
  metric_fn: "metrics:accuracy"
YAML

echo "--- 3) lock ---"
"$PY" "$FALSIFY" lock smoke_demo

echo "--- 4) run ---"
"$PY" "$FALSIFY" run smoke_demo

echo "--- 5) verdict ---"
VERDICT_OUT=$("$PY" "$FALSIFY" verdict smoke_demo)
echo "$VERDICT_OUT"

echo "--- 6) list ---"
"$PY" "$FALSIFY" list

if ! echo "$VERDICT_OUT" | grep -q "PASS"; then
    echo "SMOKE FAIL: verdict output did not contain 'PASS'" >&2
    exit 1
fi

echo
echo "smoke test: PASS"
