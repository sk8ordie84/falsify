#!/usr/bin/env bash
#
# demo.sh — auto-narrated end-to-end walkthrough of Falsification Engine.
#
# Runs the JUJU fixture through lock/run/verdict (PASS), then tampers the
# threshold inside .falsify/juju/spec.yaml and shows diff → re-lock → FAIL
# → guard block. Restores state at the end so the repo is clean after.
#
# Usage:
#   ./demo.sh              # with 2-second pauses between scenes
#   DEMO_AUTO=1 ./demo.sh  # no pauses (CI-friendly)

set -euo pipefail

# ANSI colors only when stdout is a TTY.
if [ -t 1 ]; then
    BOLD=$'\033[1m'
    CYAN=$'\033[36m'
    GREEN=$'\033[32m'
    RED=$'\033[31m'
    DIM=$'\033[2m'
    ITALIC=$'\033[3m'
    RESET=$'\033[0m'
else
    BOLD=""
    CYAN=""
    GREEN=""
    RED=""
    DIM=""
    ITALIC=""
    RESET=""
fi

section() {
    printf "\n%s%s== %s ==%s\n\n" "$BOLD" "$CYAN" "$1" "$RESET"
}

narrate() {
    printf "%s%s> %s%s\n" "$DIM" "$ITALIC" "$1" "$RESET"
}

pause() {
    if [ "${DEMO_AUTO:-}" != "1" ]; then
        sleep 2
    fi
}

# Preconditions — fail early with a clear message.
if ! command -v python3 >/dev/null 2>&1; then
    echo "demo.sh: python3 not found on PATH" >&2
    exit 1
fi
if [ ! -f falsify.py ]; then
    echo "demo.sh: falsify.py not found — run from the repo root" >&2
    exit 1
fi
if [ ! -d examples/juju_sample ]; then
    echo "demo.sh: examples/juju_sample/ missing" >&2
    exit 1
fi

# Pre-flight backup: if anything goes sideways, examples/juju_sample/spec.yaml
# can be recovered from this copy. Trap restores it on abnormal exit.
SPEC_BACKUP="/tmp/juju_spec_demo_backup.$$.yaml"
cp examples/juju_sample/spec.yaml "$SPEC_BACKUP"

cleanup() {
    local code=$?
    if [ "$code" -ne 0 ] && [ -f "$SPEC_BACKUP" ]; then
        cp "$SPEC_BACKUP" examples/juju_sample/spec.yaml
    fi
    rm -f \
        examples/juju_sample/spec.yaml.tmp \
        examples/juju_sample/spec.yaml.bak \
        .falsify/juju/spec.yaml.bak \
        "$SPEC_BACKUP" 2>/dev/null || true
}
trap cleanup EXIT

# Idempotent clean slate: reset the threshold line to 0.25 regardless of
# whatever a previous demo run left behind, and wipe any prior .falsify/juju.
sed -i.tmp 's/threshold: 0\.[0-9][0-9]*$/threshold: 0.25/' examples/juju_sample/spec.yaml
rm -f examples/juju_sample/spec.yaml.tmp

rm -rf .falsify/juju
mkdir -p .falsify/juju
cp examples/juju_sample/spec.yaml .falsify/juju/spec.yaml

# ----------------------------------------------------------------------
section "Scene 1 — Lock the hypothesis"
narrate "We declare the claim and lock the spec with a SHA-256 hash."
python3 falsify.py lock juju
pause

# ----------------------------------------------------------------------
section "Scene 2 — Run and verdict (expect PASS)"
python3 falsify.py run juju
set +e
python3 falsify.py verdict juju
VERDICT_PASS=$?
set -e
printf "%sExit code: %d%s\n" "$GREEN" "$VERDICT_PASS" "$RESET"
pause

# ----------------------------------------------------------------------
section "Scene 3 — Tamper with the threshold"
narrate "Someone tightens threshold from 0.25 to 0.15 after the fact."
sed -i.bak 's/threshold: 0\.25$/threshold: 0.15/' .falsify/juju/spec.yaml
set +e
python3 falsify.py diff juju
DIFF_EXIT=$?
set -e
printf "%sDiff exit code: %d%s\n" "$RED" "$DIFF_EXIT" "$RESET"
pause

# ----------------------------------------------------------------------
section "Scene 4 — Re-lock, re-run, verdict (expect FAIL)"
python3 falsify.py lock juju --force
python3 falsify.py run juju
set +e
python3 falsify.py verdict juju
VERDICT_FAIL=$?
set -e
printf "%sExit code: %d%s\n" "$RED" "$VERDICT_FAIL" "$RESET"
pause

# ----------------------------------------------------------------------
section "Scene 5 — Guard blocks a contradicting commit message"
set +e
python3 falsify.py guard "brier below 0.15 confirmed"
GUARD_EXIT=$?
set -e
printf "%sGuard exit code: %d%s\n" "$RED" "$GUARD_EXIT" "$RESET"
pause

# ----------------------------------------------------------------------
section "Restoring state"
cp examples/juju_sample/spec.yaml .falsify/juju/spec.yaml
python3 falsify.py lock juju --force >/dev/null
rm -f .falsify/juju/spec.yaml.bak
printf "%sDone. spec.yaml restored to threshold 0.25.%s\n" "$GREEN" "$RESET"

# ----------------------------------------------------------------------
section "Summary"
echo "Scene 2 verdict:  $VERDICT_PASS  (0 = PASS)"
echo "Scene 3 diff:     $DIFF_EXIT  (3 = hash mismatch)"
echo "Scene 4 verdict:  $VERDICT_FAIL  (10 = FAIL)"
echo "Scene 5 guard:    $GUARD_EXIT  (11 = guard violation)"
