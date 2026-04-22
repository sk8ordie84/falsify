#!/usr/bin/env bash
# Automated falsify demo driver. Designed to be wrapped by asciinema:
#     asciinema rec docs/assets/demo.cast -c "bash scripts/record_demo.sh"
#
# Simulates human typing with per-keystroke jitter so the recorded
# asciicast feels real. Set TYPING=0 for a silent raw dry-run that
# only checks whether the command sequence produces the expected
# exit codes.
#
# Environment knobs:
#   TYPING=1|0       (default 1) — per-keystroke animation on/off
#   PRE_SLEEP=0.8    seconds of quiet before each command is typed
#   POST_SLEEP=1.2   seconds of quiet after each command finishes
#   REPO=<path>      path to the falsify repo (default: absolute)

set -u
set -o pipefail

REPO="${REPO:-/Users/cuneytozturk/Desktop/falsify-hackathon}"
VENV="$REPO/.venv-demo"
TYPING="${TYPING:-1}"
PRE_SLEEP="${PRE_SLEEP:-2.0}"
POST_SLEEP="${POST_SLEEP:-5.0}"
BREATHE_SLEEP="${BREATHE_SLEEP:-2.5}"

# -------- helpers --------

_type_string() {
    # Delegate the whole per-keystroke loop to python so stdout stays
    # flushed on every char — bash `printf` block-buffers when asciinema
    # records without a TTY, collapsing the animation to zero duration.
    python3 - "$1" <<'PY'
import os, random, sys, time
s = sys.argv[1]
for ch in s:
    sys.stdout.write(ch)
    sys.stdout.flush()
    time.sleep(random.uniform(0.040, 0.080))
PY
}

run_step() {
    local cmd="$1"
    sleep "$PRE_SLEEP"
    if [[ "$TYPING" == "1" ]]; then
        printf '$ '
        _type_string "$cmd"
        printf '\n'
    else
        printf '$ %s\n' "$cmd"
    fi
    # `set +e` around eval so tamper (exit 3) does not abort the script.
    set +e
    eval "$cmd"
    local rc=$?
    set -e
    set +e
    sleep "$POST_SLEEP"
    return "$rc"
}

# -------- bootstrap --------

# Venv must exist (one-time setup is documented in the dry-run
# prep guide). If missing, bail with a clear error rather than
# silently install during a take.
if [[ ! -d "$VENV" ]]; then
    echo "record_demo: venv not found at $VENV" >&2
    echo "record_demo: create it once with:" >&2
    echo "    python3.11 -m venv $VENV && source $VENV/bin/activate && pip install -e $REPO" >&2
    exit 1
fi

export VIRTUAL_ENV_DISABLE_PROMPT=1
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# Idempotent re-install keeps dev edits fresh between takes.
pip install -e "$REPO" --quiet >/dev/null 2>&1 || true

cd "$(mktemp -d)"
export PS1='$ '
clear

# Opening blank pause.
sleep 1

# -------- shot list from docs/DEMO_SCRIPT.md --------

# Shot 4 (0:26-0:40) — scaffold + lock
run_step "falsify init --template accuracy --name acc && falsify lock acc"
sleep "$BREATHE_SLEEP"

# Shot 5 (0:40-0:54) — run + verdict PASS
run_step 'falsify run acc && falsify verdict acc; echo "exit: $?"'
sleep "$BREATHE_SLEEP"

# Shot 6 (0:54-1:08) — silent tamper; expect exit 3
run_step "sed -i '' 's/0.80/0.70/' .falsify/acc/spec.yaml && falsify run acc; echo \"exit: \$?\""
sleep "$BREATHE_SLEEP"

# Shot 7 (1:08-1:18) — honest relock + audit trail
run_step "falsify lock acc --force && falsify export --output audit.jsonl && head -2 audit.jsonl"

# Closing blank pause.
sleep 1
