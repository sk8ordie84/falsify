# Demo video script — 90 seconds

## Target

90-second run-time, 1080p60, silent-compatible with captions
burned in. Optional TTS voiceover — ElevenLabs "Rachel" (clear,
neutral) or "Adam" (lower register) both work. No on-camera
presenter. Designed for end-to-end offline recording; no live
typing.

## Shot list

| Time       | Dur. | Shot                             | Voiceover                                                                                                              | On-screen text                     | Terminal command                                           |
|------------|------|----------------------------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------|------------------------------------------------------------|
| 0:00-0:05  | 5s   | Title card. Hard cut in.         | (silence)                                                                                                              | falsify -- Git for AI honesty       | (none)                                                     |
| 0:05-0:12  | 7s   | Close-up of a release note.      | Your team claims ninety-two percent accuracy. Someone lowered the threshold last Tuesday. You did not notice.          | The lie you did not catch         | (none)                                                     |
| 0:12-0:20  | 8s   | Text-only slide, dissolve.       | Falsify fixes that. Pre-register the claim before you see the data. A cryptographic hash locks the spec.               | Lock before you run                | (none)                                                     |
| 0:20-0:32  | 12s  | Terminal; text overlay "scaffold".| Any edit changes the hash, and the run refuses to proceed. Initialize a new claim from a template. Lock it.            | hash = spec fingerprint            | `falsify init --template accuracy` then `falsify lock accuracy` |
| 0:32-0:45  | 13s  | Terminal; highlight PASS line.   | The hash is now a fingerprint. Run the experiment. The verdict is PASS with exit code zero.                            | PASS, exit 0                       | `falsify run accuracy && falsify verdict accuracy; echo "exit: $?"` |
| 0:45-0:58  | 13s  | Terminal; red tint on exit code. | Now watch what happens when someone tampers. Edit the threshold silently. Run again. Exit code three. The lie is blocked automatically. | The lie is blocked automatically | `sed -i '' 's/0.80/0.70/' .falsify/accuracy/spec.yaml && falsify run accuracy; echo "exit: $?"` |
| 0:58-1:10  | 12s  | Terminal; show JSONL audit line. | The honest fix is to re-lock with force, which leaves a visible audit entry. Falsify export writes the chain as JSON lines. | Relock = audit entry               | `falsify lock accuracy --force && falsify export --output audit.jsonl` |
| 1:10-1:22  | 12s  | Three quick cuts, 4s each.       | Four Claude Code skills, two subagents, three slash commands, and one Model Context Protocol server compose the workflow. | Claude Code composes the workflow | `/new-claim accuracy` -> claim-review on a PR diff -> MCP query |
| 1:22-1:28  | 6s   | Stats card, fade.                | Falsify ships with standard library code and one dependency, and uses itself to verify its own properties.            | stdlib + 1 dep. Self-dogfooded.    | (none)                                                     |
| 1:28-1:30  | 2s   | End card. Fade out.              | Lock the claim before the data.                                                                                        | github.com/<user>/falsify          | (none)                                                     |

Transition convention: hard cut between terminal shots; dissolve
between text slides; text overlays fade in at 150ms, hold, fade
out at 150ms.

## Voiceover full script

Paste this block into ElevenLabs (or any TTS engine) as one take.
Target pace is 125 words per minute; 10 seconds of silent
terminal action are reserved around the money shot. Sentences are
kept under 15 words for TTS clarity; no contractions; no idioms.

> Your team claims ninety-two percent accuracy. Someone lowered
> the threshold last Tuesday. You did not notice. Falsify fixes
> that. Pre-register the claim before you see the data. A
> cryptographic hash locks the spec. Any edit changes the hash,
> and the run refuses to proceed. Initialize a new claim from a
> template. Lock it. The hash is now a fingerprint. Run the
> experiment. The verdict is PASS with exit code zero. Now watch
> what happens when someone tampers. Edit the threshold silently.
> Run again. Exit code three. The lie is blocked automatically.
> The honest fix is to re-lock with force, which leaves a visible
> audit entry. Falsify export writes the chain as JSON lines.
> Four Claude Code skills, two subagents, three slash commands,
> and one Model Context Protocol server compose the workflow.
> Falsify ships with standard library code and one dependency,
> and uses itself to verify its own properties. Lock the claim
> before the data.

## Recording notes

- Record at 1080p60. Terminal capture via `asciinema` plus
  `asciinema-agg` to MP4, or OBS with a window capture source.
- Terminal: fixed-width font at 18pt, 80-column width, solid
  dark background (`#0c0c0c`) for legibility.
- Use a throwaway directory (`mktemp -d && cd "$_"`) so no real
  user data, shell history, or paths appear in frame.
- Record each terminal segment separately and cut in post; do
  not live-type — typos and pauses ruin the pace.
- Audio: apply a noise gate to the TTS output; normalize to
  minus 3 LUFS integrated loudness; no music, or very quiet
  ambient pad at minus 30 LUFS if silence feels uncomfortable.
- Color-grade the red tint for the exit-code-3 shot in post; do
  not tint the live terminal.

## Captions

Paste this block verbatim into `demo.srt`. Burn in for silent
autoplay compatibility.

    1
    00:00:00,000 --> 00:00:05,000
    falsify -- Git for AI honesty

    2
    00:00:05,000 --> 00:00:12,000
    Your team claims ninety-two percent accuracy. Someone lowered the threshold last Tuesday. You did not notice.

    3
    00:00:12,000 --> 00:00:20,000
    Falsify fixes that. Pre-register the claim before you see the data. A cryptographic hash locks the spec.

    4
    00:00:20,000 --> 00:00:32,000
    Any edit changes the hash, and the run refuses to proceed. Initialize a new claim from a template. Lock it.

    5
    00:00:32,000 --> 00:00:45,000
    The hash is now a fingerprint. Run the experiment. The verdict is PASS with exit code zero.

    6
    00:00:45,000 --> 00:00:58,000
    Now watch what happens when someone tampers. Edit the threshold silently. Run again. Exit code three. The lie is blocked automatically.

    7
    00:00:58,000 --> 00:01:10,000
    The honest fix is to re-lock with force, which leaves a visible audit entry. Falsify export writes the chain as JSON lines.

    8
    00:01:10,000 --> 00:01:22,000
    Four Claude Code skills, two subagents, three slash commands, and one Model Context Protocol server compose the workflow.

    9
    00:01:22,000 --> 00:01:28,000
    Falsify ships with standard library code and one dependency, and uses itself to verify its own properties.

    10
    00:01:28,000 --> 00:01:30,000
    Lock the claim before the data.

## Checklist before record

- Fresh tmux session; no prior panes or history visible.
- `clear && history -c` before each take.
- `export PS1='$ '` — minimal prompt, no user/host/path leak.
- `mktemp -d` working directory; confirm `pwd` is anonymized.
- Terminal font 18pt; window sized to 80 columns x 24 rows.
- GitHub URL rendered large in the final frame's end card.
- Verify `asciinema --version` and `asciinema-agg --version`.
- Dry-run the full sequence once without recording.
- Silence Slack, Mail, and system notifications.
- Close all other windows to prevent accidental focus steal.

## Checklist before upload

- Captions burned in (not sidecar SRT) for silent-autoplay.
- Audio normalized to minus 3 LUFS integrated, peaks below -1 dBTP.
- Final cut runs under 90 seconds; trim dead frames at head and tail.
- Thumbnail selected: freeze-frame of the exit-code-3 red flash.
- Shortened GitHub URL tested and verified in an incognito window.
