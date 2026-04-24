#!/usr/bin/env python3
"""Render 17 VO lines with Callum (ElevenLabs). Reads ELEVEN_KEY from env.

Writes docs/assets/vo_lines_callum/line_NN.mp3 and prints duration table.
Safe to re-run: skips existing files unless --force.
"""
from __future__ import annotations

import json, os, subprocess, sys, time
import urllib.request, urllib.error
from pathlib import Path

VOICE_ID = "N2lVS1w4EtoT3dr4eOWO"  # Callum
MODEL = "eleven_multilingual_v2"
OUT_DIR = Path("docs/assets/vo_lines_callum")

SETTINGS = {
    "stability": 0.45,
    "similarity_boost": 0.75,
    "style": 0.35,
    "use_speaker_boost": True,
}

LINES = [
    "Your team claims ninety-four percent accuracy.",
    "A radiologist trusts it.",
    "Three weeks later, the real number is seventy-one.",
    "The claim was never falsifiable.",
    "Tests passed. Review approved.",
    "Falsify fixes that.",
    "Pre-register the claim. Hash it. Lock it.",
    "A cryptographic fingerprint of the spec.",
    "Locked.",
    "Run. Verdict: pass. Exit zero.",
    "Now — a silent edit.",
    "Exit three. The lie is blocked.",
    "The audit trail writes itself.",
    "Every verdict, cryptographically chained.",
    "Five skills. Two subagents. Three commands. One MCP.",
    "Lock the claim before the data.",
    "Or it didn't happen.",
]

FORCE = "--force" in sys.argv


def render_line(idx: int, text: str, api_key: str) -> Path:
    out_path = OUT_DIR / f"line_{idx:02d}.mp3"
    if out_path.exists() and not FORCE:
        return out_path
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_192"
    payload = {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out_path.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} on line {idx}: {e.read()!r}\n")
        raise
    return out_path


def duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def main() -> int:
    key = os.environ.get("ELEVEN_KEY", "")
    if len(key) < 20:
        sys.stderr.write("ELEVEN_KEY missing\n")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assert len(LINES) == 17, f"expected 17 got {len(LINES)}"

    print(f"Rendering {len(LINES)} lines with Callum (voice {VOICE_ID})")
    print(f"Settings: {SETTINGS}\n")

    for i, text in enumerate(LINES, start=1):
        t0 = time.monotonic()
        p = render_line(i, text, key)
        d = duration(p)
        status = "ok" if 0.5 <= d <= 5.0 else "OUT_OF_RANGE"
        age = time.monotonic() - t0
        print(f"line_{i:02d}  {d:5.2f}s  {status}  ({age:.1f}s)  {text}")
        time.sleep(0.4)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
