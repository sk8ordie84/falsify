#!/usr/bin/env python3
"""Render v3.3 hybrid VO — 17 lines, per-scene ElevenLabs settings."""
from __future__ import annotations

import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Brian
MODEL = "eleven_multilingual_v2"
OUT_DIR = Path("docs/assets/vo_lines")

# (text, stability, similarity_boost, style, speaker_boost)
LINES = [
    ("Production radiology classifier.",                                           0.42, 0.78, 0.18, True),   # 01 sc01
    ("Ninety-four percent accurate — that was the claim.",                         0.42, 0.78, 0.18, True),   # 02 sc01
    ("The actual number was seventy-one.",                                         0.42, 0.78, 0.22, True),   # 03 sc01 (slightly more style on the drop)
    ("Nobody lied, exactly.",                                                      0.62, 0.78, 0.04, True),   # 04 sc02
    ("The claim just wasn't written anywhere it couldn't be rewritten.",           0.62, 0.78, 0.04, True),   # 05 sc02
    ("That's the problem falsify solves.",                                         0.30, 0.80, 0.28, True),   # 06 sc03
    ("Before the experiment runs — you commit to the metric, the threshold, the dataset.", 0.55, 0.78, 0.10, True),  # 07 sc04
    ("The hash is a witness.",                                                     0.55, 0.78, 0.10, True),   # 08 sc04
    ("A real run. Ten thousand samples.",                                          0.50, 0.78, 0.08, True),   # 09 sc05
    ("The threshold was locked at point-nine-four.",                               0.50, 0.78, 0.08, True),   # 10 sc05
    ("Point-nine-four-three.",                                                     0.50, 0.78, 0.08, True),   # 11 sc05
    ("Someone changes the threshold after the fact.",                              0.38, 0.78, 0.25, True),   # 12 sc06
    ("Drops it low enough to pass.",                                               0.38, 0.78, 0.25, True),   # 13 sc06
    ("It's a small edit — the kind that's easy to miss in review.",                0.38, 0.78, 0.25, True),   # 14 sc06
    ("Except the hash remembers.",                                                 0.72, 0.78, 0.03, True),   # 15 sc06 deadpan
    ("Every claim — sealed before the data.",                                      0.48, 0.78, 0.12, True),   # 16 sc07
    ("Or it didn't happen.",                                                       0.48, 0.78, 0.12, True),   # 17 sc07
]


def render(idx: int, text: str, stab: float, sim: float, style: float, boost: bool, key: str) -> Path:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_192"
    body = json.dumps({
        "text": text,
        "model_id": MODEL,
        "voice_settings": {
            "stability": stab,
            "similarity_boost": sim,
            "style": style,
            "use_speaker_boost": boost,
        },
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg",
    })
    out = OUT_DIR / f"line_{idx:02d}.mp3"
    with urllib.request.urlopen(req, timeout=90) as r:
        out.write_bytes(r.read())
    return out


def dur(p: Path) -> float:
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nk=1:nw=1",str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main() -> int:
    key = os.environ.get("ELEVEN_KEY")
    if not key:
        sys.stderr.write("ELEVEN_KEY not set\n"); return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assert len(LINES) == 17

    bad = []
    for i, (txt, st, sb, sty, bo) in enumerate(LINES, 1):
        try:
            p = render(i, txt, st, sb, sty, bo, key)
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"HTTP {e.code} line {i}: {e.read()!r}\n"); return 2
        d = dur(p)
        ok = 0.6 <= d <= 6.0
        tag = "ok" if ok else "OUT"
        if not ok: bad.append((i, d, txt))
        print(f"line_{i:02d}  {d:5.2f}s  stab={st:.2f} sty={sty:.2f}  {tag}  {txt}")
        time.sleep(0.4)

    if bad:
        print("\nWARN:", bad); return 3
    print("\nAll 17 lines rendered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
