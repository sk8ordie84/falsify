# Demo Video Shot List — Falsification Engine

Total budget 180 seconds. Hard cap 210 seconds.

## Scene 0 — Cold open (0:00–0:12, 12s)

- Visual: Black screen, white text "Falsification Engine — pre-registration + CI for AI-agent claims."
- Voiceover: "AI agents make claims. This makes those claims falsifiable — before the data arrives."
- Transition: Cut to terminal.

## Alt-Scene 0 — Docker cold open (optional swap for Scene 0)

- Visual: single terminal line — `docker run --rm -it falsify-demo`
- Cut directly to the auto-demo output scrolling.
- Voiceover: "One docker run. No Python setup. Watch the whole story."
- Use this version if we want to emphasize zero-setup install over
  the philosophical cold open.

## Scene 1 — The problem (0:12–0:30, 18s)

- Visual: Terminal showing fake agent output: My model achieves 92 percent accuracy.
- Voiceover: "An agent says 92 percent. What was the threshold? What was the metric? When did we decide? Without pre-registration, we're just story-telling."
- Cursor runs: ls .falsify/ — empty.

## Scene 2 — Lock the hypothesis (0:30–0:55, 25s)

Commands (typed live):

    python3 falsify.py init juju
    python3 falsify.py lock juju

- Voiceover: "We declare the claim, metric, threshold before running anything. Lock it. Hash freezes the spec."
- Visual highlight: zoom on LOCKED juju — hash a3f9c12b.

## Scene 3 — Run and verdict PASS (0:55–1:20, 25s)

Commands:

    python3 falsify.py run juju
    python3 falsify.py verdict juju

- Voiceover: "Run. Verdict is deterministic — brier 0.21, below threshold 0.25, n=20. PASS. Exit code zero."
- Visual: green PASS line, echo $? shows 0.

## Scene 4 — Tampering test (1:20–1:50, 30s)

- Action: open spec.yaml, change threshold 0.25 to 0.15

Commands:

    python3 falsify.py diff juju

- Voiceover: "Someone edits the threshold after the fact. Diff shows exactly what changed. Hash no longer matches the lock. Exit code three."
- Visual: red diff lines, minus threshold 0.25, plus threshold 0.15.

## Scene 5 — FAIL verdict + guard (1:50–2:20, 30s)

Commands:

    python3 falsify.py lock juju
    python3 falsify.py run juju
    python3 falsify.py verdict juju
    echo "brier below 0.15 confirmed" | xargs python3 falsify.py guard

- Voiceover: "Now FAIL — brier exceeds the new threshold. And if someone tries to commit a contradicting claim, the guard blocks it. Exit code eleven."

## Scene 6 — Opus 4.7 layers (2:20–2:45, 25s)

Visual: split screen, file tree on left with highlights:

    .claude/skills/hypothesis-author/SKILL.md
    .claude/skills/falsify/SKILL.md
    .claude/skills/claim-audit/SKILL.md
    .claude/agents/claim-auditor.md
    .claude/agents/verdict-refresher.md
    .github/workflows/falsify.yml

- Voiceover: "Three Claude Code skills. Two forked-context subagents. CI gate. Opus 4.7 orchestrates all five — drafting specs, auditing text, refreshing stale verdicts."
- Micro-moment (3s max): cut to a browser showing dashboard.html generated from `falsify stats --html` — verdict cards with colored state badges, dark-mode-aware. Quick pan, then back to file tree.

## Scene 7 — Close (2:45–3:00, 15s)

- Visual: GitHub repo page, green Actions badge, MIT license visible.
- Voiceover: "Falsification Engine. Open source. Built in five days with Claude Opus 4.7. Link in the description."

## Pre-record checklist

- Terminal font size at least 18pt
- Warp clean session, no prior history visible
- rm -rf .falsify/juju before Scene 2
- spec.yaml reverted to threshold 0.25
- Editor ready on second window for Scene 4 edit
- Microphone levels tested (voiceover can be post-recorded)
- Screen resolution 1920x1080 minimum

Recording tool: QuickTime Screen Recording, no cursor highlighting, show keystrokes via terminal only, audio post-recorded over silent screencast.

## Editing targets

- Crossfade between scenes 0.2s
- Zoom-in moments: Scene 2 lock hash, Scene 4 diff lines, Scene 5 exit code 11
- Background: no music, terminal keystrokes plus voice only, serious tone.
