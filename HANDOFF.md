# falsify — v3.1 FIX brief (target: 10/10)

## v3.1 user feedback — fix these FIRST, before anything else

User watched `docs/assets/v2/falsify_demo_final_with_vo.mp4` and flagged 6 specific issues. Screenshots live in `/Users/cuneytozturk/Desktop/haq/1..6.png`. Address each before re-rendering.

### FIX 1 — sc01 subtitle font fallback
"radiology classifier — production" renders as italic serif (system fallback). Base64 font embed did not take for this scene. Target: **JetBrains Mono 400, 14px, color #7A8896, letter-spacing 0.08em, uppercase**. Verify `@font-face` block exists and base64 data URL is valid in `scripts/slides_html/01_hook.html`. Run `brand/inject_fonts.py` after edit.

### FIX 2 — sc02 headline font fallback
"The claim was never falsifiable." renders as bold serif (Times/Georgia fallback). Same root cause as FIX 1. Target: **Space Grotesk 700, 68px, color #E8EEF2**. Verify font embed in `02_problem.html`.

### FIX 3 — inner black rectangle inside green terminal frame (sc03, sc04, sc05, sc06)
Terminal container currently has `background: #050A0E` (darker than page `#0B0F14`) plus green border. The inner rectangle looks like a patch, amateur. Fix: **set container `background: transparent`**, keep only the 1px green border. Text sits directly on page bg.

Applies to:
- `04_lock.html` — terminal box (screenshot 3)
- `05_pass.html` — terminal box (screenshot 4)
- `06_tamper.html` — terminal box (screenshot 5)

Also in sc05 the **giant "PASS"** slam sits on its own black rectangle — remove that rect entirely, PASS text floats on page bg.

### FIX 4 — sc05 progress bar percentage not animating
"100%" text appears immediately at full value while bar fills. Fix: animate the counter from 0 to 100 synchronized with the width animation.

```html
<div class="bar"><div class="fill"></div></div>
<span class="pct">0%</span>
```
```css
.fill { width: 0; animation: fill 2s steps(50, end) forwards; }
@keyframes fill { to { width: 100%; } }
```
```js
// seek-compatible — drives off the same timer used by __SEEK__
const pct = document.querySelector('.pct');
const start = performance.now();
requestAnimationFrame(function tick(t){
  const p = Math.min(1, (t - start) / 2000);
  pct.textContent = Math.round(p * 100) + '%';
  if (p < 1) requestAnimationFrame(tick);
});
```
Also remove the black rect under the log lines — same transparent-bg fix as FIX 3.

### FIX 5 — sc06 inner black rect
Same issue as FIX 3. Terminal container in `06_tamper.html` — set transparent bg, keep green border only.

### FIX 6 — sc07 close layout + fonts
"Lock the claim before the data." + "Or it didn't happen." render in fallback serif. Chevron lockup drifts left of center. Layout feels disorganized.

Fix:
- Rebuild `07_close.html` using a single flex column, centered, equal gap (60px between major elements).
- Verify `@font-face` base64 loads — use same block as `01_hook.html` known-good.
- Tagline target: **Space Grotesk 400, 36px, color #E8EEF2, center aligned**.
- Sub: **Space Grotesk 400, 28px, color #7A8896, center aligned**.
- Lockup SVG: center horizontally, 400px wide.
- GitHub URL: **JetBrains Mono 18px, #39D98A, center aligned**.
- Honesty chip: stays bottom-center.

### FIX 7 — VO is soulless and flat
User: "anlatım cok ruhsuz ve dogal degil". Brian read lines too even. Fix in ElevenLabs settings:

```
stability: 0.45      (lower → more variation, more human)
similarity_boost: 0.70
style: 0.40          (higher → more expressive)
speaker_boost: true
```

Rewrite lines with explicit breath punctuation for natural cadence:

```
01  Your team claims... ninety-four percent accuracy.
02  A radiologist trusts it.
03  Three weeks later, a customer proves the real number — is seventy-one.
04  The claim was never falsifiable.
05  Tests passed. Review approved.
06  Falsify fixes that.
07  Pre-register the claim. Hash it. Lock it.
08  A cryptographic fingerprint of the spec.
09  Locked.
10  Run. Verdict — pass. Exit zero.
11  Now... a silent edit.
12  Exit three. The lie — is blocked.
13  The audit trail writes itself.
14  Every verdict, cryptographically chained.
15  Five skills. Two subagents. Three commands. One MCP.
16  Lock the claim before the data.
17  Or it didn't happen.
```

### PIPELINE CHANGE — silent first, VO last

User request, and it's the correct pro workflow:
1. Fix all 6 visual issues above
2. Re-render scenes + concat + radar composite
3. Produce **silent 90s video**
4. User reviews silent video — confirm picture lock
5. Only then record VO line-by-line, pin to timecodes
6. Mix audio bed + VO + SFX
7. Final mux

Do NOT record VO before user approves silent cut.

---

# falsify — v3 rebuild brief (target: 10/10)

**Deadline:** Apr 26 20:00 EST. Cerebral Valley "Built with Opus 4.7" hackathon, $50K prize. User loses computer access Sat Apr 25 — ship Friday. Turkish responses.

**WHY v2 FAILED (do not repeat):** previous session only re-timed VO over unchanged video. The scenes don't have dramatic beats to sync to. Radar spins, text wipes, nothing *happens*. The "94 → 71" line is the emotional core of the pitch and the scene ignores it. Rebuilding audio over a flat video gives you a flat video with cleaner audio. Same result.

**v3 mandate:** you must rewrite scene HTMLs to create REAL beats, re-render the video, then record VO to match. Audio-only passes are forbidden.

---

## Read first (orient)

1. `README.md` — product
2. `scripts/slides_html/01_hook.html` through `07_close.html` — current scenes (rewrite most)
3. `scripts/render_video_assets.py` — Playwright renderer, `scene <n>` and `radar-hero` modes
4. `scripts/radar/claim-radar.html` — deterministic radar, keep as-is
5. `docs/assets/v2/falsify_demo_final.mp4` — current 3/10 output (watch once, note what's flat)
6. `/Users/cuneytozturk/Downloads/FaxMachine1987Promo_standalone.html` — user's reference for pacing and fax-printer motion language

---

## What makes it amateur now

- Every scene uses the same `clip-path inset steps line-reveal`. Monotone.
- No visual contrast between "the lie" (sc01, sc02, sc06a) and "the fix" (sc03, sc04, sc05, sc07).
- No screen shake, no glitch, no red tear, no zoom. Camera is frozen.
- Radar is decorative. TAMPERED node blinks — there's no causal coupling to the "71%" line.
- "94 → 71" is not a reveal. 94 appears, holds, radar does its thing, 71 is never shown on screen. This is the single worst miss.
- Green-on-dark everywhere. "Lie" moments need RED tear; "lock/pass" moments stay green.
- No typography hierarchy inside scenes — everything is same size, same weight.

---

## v3 scene rebuild spec

Durations stay locked: 11 / 7 / 10 / 14 / 16 / 20 / 12 = 90s.

### sc01 — hook (11s) — CENTERPIECE, rebuild hardest

```
t=0.0   fade in, centered: "94%" JetBrains Mono 240px, signal-green #39D98A
        subtitle below, 28px muted: "radiology classifier — production"
t=0.5   VO: "Your team claims ninety-four percent accuracy."
t=2.5   bottom-right: small radar mini (360×360, transparent) fades in
t=3.0   VO: "A radiologist trusts it."
t=3.2   subtle zoom: scale 1.00 → 1.03 ease-out 2s on the stage
t=5.0   RADAR SWEEP finds TAMPERED node, red flash #FF4D6D at coordinates
t=5.3   SCREEN SHAKE 120ms, amplitude 8px, 6 cycles, cubic-bezier
        SIMULTANEOUS: "94%" number tears — horizontal glitch offset 20px for 80ms
t=5.5   VO: "Three weeks later a customer proves the real number is seventy-one."
t=5.5   "94%" gets STRIKETHROUGH red line drawn across (200ms steps(10))
t=6.0   "94%" wipes out upward, "71%" wipes in from below in RED #FF4D6D, 300ms steps(12)
        subtitle changes to: "actual — measured by customer"
t=6.5   static red vignette pulses once (opacity 0 → 0.2 → 0 over 400ms)
t=8.0   freeze, hold
t=10.5  quick fade to black 500ms
```

This is the scene the jury will remember. Spend the most time here. Use absolute positioning for the numbers so you can swap them cleanly. CSS keyframes with `steps(N)` for all reveals.

### sc02 — problem (7s)

```
t=0.0   red accent still lingering — top-left micro tag "TAMPERED" blinking steps(2) at 2Hz for 1.5s
t=0.5   VO: "The claim was never falsifiable."
        text block fax-prints line by line (current style, keep):
        "No locked metric."
        "No locked threshold."
        "No locked dataset."
t=3.5   VO: "Tests passed. Review approved."
t=4.0   green CI-style checkmarks tick beside those three lines, 150ms apart
        (this is the DARK JOKE — checkmarks on top of the red warning = the lie)
t=5.5   red vignette returns, opacity 0.15, hold
t=6.5   cut
```

### sc03 — promise (10s)

```
t=0.0   BLACK, total silence 500ms
t=0.5   falsify lockup (brand/lockup.svg) wipes in center, steps(12) 600ms
t=1.5   hold 1s
t=2.5   lockup shrinks to top, "FALSIFY FIXES THAT." slams in underneath
        JetBrains Mono 64px, all-caps, tracking 0.12em
t=3.0   VO: "Falsify fixes that."
t=5.5   VO: "Pre-register the claim. Hash it. Lock it."
t=5.5   three-word rhythm: "PRE-REGISTER." "HASH IT." "LOCK IT." each slams 250ms apart
        stepped appearance (scale 1.15 → 1.00, 80ms linear) for each word
t=9.0   cut
```

### sc04 — lock (14s)

```
t=0.0   terminal frame appears, JetBrains Mono 22px
        $ falsify lock claim-001.yaml
t=0.5   printer-prints the YAML block (fax motion, reuse current sc04):
        claim: accuracy
        threshold: 0.94
        dataset: sha256:2f3a...
t=4.0   VO: "A cryptographic fingerprint of the spec."
t=5.5   SHA-256 hash prints char-by-char, 28 chars × 40ms = 1.12s
        steps(28) mono reveal, each char lands with a soft typewriter click (synced in audio)
t=7.5   hash completes, 200ms hold
t=8.0   LOCKED stamp slams across the terminal, red→green transition
        scale 1.25 → 1.00 over 100ms linear, opacity 0→1 80ms
t=8.2   VO: "Locked."  (single word, punch)
t=8.5   green glow pulse around terminal 400ms
t=10.0  exit-code line: "exit 0" appears in green
t=13.5  cut
```

### sc05 — pass (16s)

```
t=0.0   $ falsify run experiment.yaml  (prompt types)
t=1.0   log lines stream, JetBrains Mono 18px, faster steps(40) line-reveals
        "loading dataset... ok"
        "threshold locked at 0.94"
        "running 10000 samples..."
        progress bar fills (CSS width animation, steps(50) 2s)
t=4.5   "accuracy: 0.943" prints
t=5.0   VO: "Run. Verdict: pass. Exit zero."
t=5.5   giant "PASS" slams into center, green, 180px
        subtle zoom 1.00 → 1.02 over rest of scene
t=7.0   "exit 0" in small mono under it
t=9.0   hold
t=15.5  fade
```

### sc06 — tamper (20s) — SECOND CENTERPIECE

```
t=0.0   same terminal as sc04 returns
t=0.5   $ vim claim-001.yaml  (opens)
t=1.0   cursor moves to threshold line
t=2.0   "0.94" backspaces char-by-char (4 chars, 100ms each, audible backspace ticks)
t=2.4   "0.71" types in red (yes, red — this is the lie being written)
t=3.5   :wq
t=5.0   $ falsify run experiment.yaml
t=7.0   VO: "Now — a silent edit."
t=7.0   red sweep across entire screen, diagonal wipe 300ms steps(15)
t=9.0   log lines stream (same as sc05 initially)
t=9.5   then: "hash mismatch detected" prints RED
t=10.0  VO: "Exit three. The lie is blocked."
t=10.0  EXIT 3 slams full-screen, red, 200px, screen shake 150ms
t=11.5  red vignette pulses
t=13.0  terminal clears
t=14.0  "audit chain" header appears
t=14.5  VO: "The audit trail writes itself."
t=14.5  chain of 5 hash blocks connects with drawn lines (SVG line stroke-dasharray animation, steps(20) 2s)
        each block: 8-char hash, timestamp, verdict (pass/pass/pass/pass/**BLOCKED**)
t=17.5  VO: "Every verdict, cryptographically chained."
t=17.5  final link to red "BLOCKED" node draws
t=19.5  cut
```

### sc07 — close (12s)

Current close is fine structurally — keep lockup reveal and tagline. Additions:

```
t=0.0   lockup reveal (existing)
t=2.0   inventory line appears (JetBrains Mono 24px):
        "5 skills · 2 subagents · 3 commands · 1 MCP"
t=3.0   VO: "Five skills, two subagents, three commands, one MCP."
t=6.5   "Lock the claim before the data." (existing)
t=8.0   VO: "Lock the claim before the data."
t=9.5   "Or it didn't happen." (existing)
t=10.2  VO: "Or it didn't happen."
t=10.7  Honesty Score chip slams (existing)
t=11.0  GitHub URL line
t=12.0  end
```

---

## Implementation rules

- **Keep palette tight:** `--fg: #E8EEF2`, `--green: #39D98A`, `--red: #FF4D6D`, `--muted: #7A8896`, `--bg: #0B0F14`. Red only in lie/error beats. Green only in locked/pass beats.
- **All motion is stepped.** `steps(N, end)` for reveals (N = 8–40 depending on length). No ease-out cubic for text. Zoom can use ease-out.
- **Screen shake:** CSS keyframes on the `.stage`, translate3d with 6 keyframes across 120ms, amplitude 8px horizontal only.
- **Fonts:** Space Grotesk 700 display, JetBrains Mono 400 technical. Embedded as base64 via `brand/inject_fonts.py` — run it after writing every SVG and before rendering.
- **Corner frame** (green L-brackets) stays on every scene for continuity.
- **REV.0.1.0 + falsify wordmark** top corners — existing.

---

## Render pipeline

1. Rewrite sc01 (most work), then sc02, sc04, sc06 (centerpieces). sc03, sc05, sc07 lighter edits.
2. `python3 scripts/render_video_assets.py scene 1` … `scene 7` — verify each renders at correct duration.
3. If `scripts/render_video_assets.py` can't handle new animations, extend it — don't work around it.
4. Radar hero composite stays (sc01 bottom-right overlay, t=1–10.5s) — user liked this.
5. Scene concat:
   ```
   ffmpeg -y -f concat -safe 0 -i concat.txt -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p docs/assets/v2/_build/scenes_v3.mp4
   ```
6. Composite radar mini onto sc01 (existing overlay filter from prior build).

---

## VO — record LAST, not first

Record only after video v3 is rendered and previewed. Watch the silent video, confirm beats land where spec says, THEN run VO lines to lock picture.

Per-line render (ElevenLabs):
- Voice: `nPczCjzI2devNBz1zQrb` (Brian)
- Model: `eleven_multilingual_v2`
- Settings: stability 0.55, similarity_boost 0.75, style 0.20, speaker_boost true
- Format: `mp3_44100_192`
- One file per line → `docs/assets/vo_lines/line_01.mp3` … `line_17.mp3`
- Verify each 0.8s ≤ duration ≤ 5.0s; rephrase-retry if over

**Credentials (env only, never hardcode):**
```
ELEVEN_KEY=<user will export before launching claude>
VOICE_ID=nPczCjzI2devNBz1zQrb
```

Line texts (exact):
```
01  Your team claims ninety-four percent accuracy.
02  A radiologist trusts it.
03  Three weeks later a customer proves the real number is seventy-one.
04  The claim was never falsifiable.
05  Tests passed. Review approved.
06  Falsify fixes that.
07  Pre-register the claim. Hash it. Lock it.
08  A cryptographic fingerprint of the spec.
09  Locked.
10  Run. Verdict: pass. Exit zero.
11  Now — a silent edit.
12  Exit three. The lie is blocked.
13  The audit trail writes itself.
14  Every verdict, cryptographically chained.
15  Five skills, two subagents, three commands, one MCP.
16  Lock the claim before the data.
17  Or it didn't happen.
```

Timecodes (delay in ms for `adelay`):
```
01:500   02:3000   03:5500
04:11500 05:14500
06:18500 07:22000
08:28000 09:32200
10:36000
11:42400 12:45000 13:52000 14:60000
15:68000 16:78000 17:82200
```

---

## SFX bed (90s, mix with VO)

```
pink noise:   anoisesrc=d=90:c=pink:a=0.02:r=48000,lowpass=f=350,volume=0.04
backspace × 4: sine=f=800:d=0.02 vol=0.20 adelay=72000,72100,72200,72300  (sc06)
fax chirps × 6: sine=f=1200:d=0.04 vol=0.25 adelay=28500,28780,29060,29340,29620,29900
typewriter × 28: sine=f=1500:d=0.015 vol=0.15 adelay=33500+40i for i in 0..27 (sc04 hash)
LOCKED slam:  sine=f=80:d=0.12  vol=0.35 adelay=32200
PASS slam:    sine=f=100:d=0.15 vol=0.30 adelay=41500
red sweep:    sine=f=600:d=0.30 vol=0.18 adelay=42400
EXIT3 low:    sine=f=60:d=0.22  vol=0.55 adelay=45000
EXIT3 mid:    sine=f=200:d=0.18 vol=0.35 adelay=45000
strikethrough whoosh: sine=f=400:d=0.20 vol=0.22 adelay=5500 (sc01)
number-swap thud:     sine=f=90:d=0.10  vol=0.40 adelay=6000 (sc01)
chip settle:  sine=f=2000:d=0.06 vol=0.10 adelay=82200
```

Final chain after amix: `alimiter=limit=0.89, loudnorm=I=-16:TP=-1:LRA=11`.

---

## Mux + sanity

```
ffmpeg -y -i docs/assets/v2/_build/video_v3_composited.mp4 \
  -i docs/assets/v2/_build/audio_v3.m4a \
  -c:v copy -c:a copy -movflags +faststart \
  docs/assets/v2/falsify_demo_final.mp4

ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,channels \
  docs/assets/v2/falsify_demo_final.mp4
```

Expect: 90.00s ±0.05, 1920×1080, h264, aac stereo.

Then `open docs/assets/v2/falsify_demo_final.mp4` — user reviews.

---

## Done criteria

- User watches, rates ≥8/10 and approves.
- Only then: `<USER>` → real handle, SUBMISSION.md refresh, public push, Cerebral Valley form.
- **Remind user to rotate ElevenLabs key** (leaked in prior chat).

---

## Forbidden

- Do NOT re-render audio without rebuilding scenes. That's what failed last time.
- Do NOT add new fonts, colors, or motion vocabularies beyond this brief.
- Do NOT shorten or extend any scene duration.
- Do NOT commit or push until user approves final cut.
