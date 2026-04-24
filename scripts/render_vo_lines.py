#!/usr/bin/env python3
"""Render 17 VO lines from ElevenLabs, one MP3 per line.

Reads ELEVEN_KEY from env. Writes docs/assets/vo_lines/line_NN.mp3.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Brian
MODEL = "eleven_multilingual_v2"
OUT_DIR = Path("docs/assets/vo_lines")

LINES = [
    "Your team claims ninety-four percent accuracy.",
    "A radiologist trusts it.",
    "Three weeks later a customer proves the real number is seventy-one.",
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
    "Five skills, two subagents, three commands, one MCP.",
    "Lock the claim before the data.",
    "Or it didn't happen.",
]


def render_line(idx: int, text: str, api_key: str) -> Path:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_192"
    payload = {
        "text": text,
        "model_id": MODEL,
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.75,
            "style": 0.20,
            "use_speaker_boost": True,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    out_path = OUT_DIR / f"line_{idx:02d}.mp3"
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} on line {idx}: {e.read()!r}\n")
        raise
    out_path.write_bytes(data)
    return out_path


def duration(path: Path) -> float:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(res.stdout.strip())


def main() -> int:
    api_key = os.environ.get("ELEVEN_KEY")
    if not api_key:
        sys.stderr.write("ELEVEN_KEY not set\n")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    assert len(LINES) == 17, f"expected 17 lines, got {len(LINES)}"

    report = []
    for i, text in enumerate(LINES, start=1):
        path = render_line(i, text, api_key)
        d = duration(path)
        status = "ok" if 0.8 <= d <= 5.0 else "OUT_OF_RANGE"
        report.append((i, d, status, text))
        print(f"line_{i:02d}  {d:5.2f}s  {status}  {text}")
        time.sleep(0.5)

    bad = [r for r in report if r[2] != "ok"]
    if bad:
        print("\nWARNING: out-of-range lines:", bad)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
