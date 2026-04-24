#!/usr/bin/env python3
"""v3.2 audio mix — Callum VO + pink bed + SFX, pinned to v3.1 video beats.

Outputs docs/assets/v2/_build/audio_v3_callum.m4a (90.00s stereo AAC).
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

VO_DIR = Path("docs/assets/vo_lines_callum")
OUT = Path("docs/assets/v2/_build/audio_v3_callum.m4a")

# Start time (ms) per VO line; tuned to actual Callum durations + post-trim
BEATS_MS = [
    500,    # 01 — HUD + 94% fade in
    3600,   # 02 — steady HUD (pushed from 3000 to avoid L01 overlap)
    5600,   # 03 — after TAMPER + 71% swap + banner
    11200,  # 04 — sc02 title reveals
    14800,  # 05 — ✓ ticks + footer
    20500,  # 06 — FALSIFY FIXES THAT slam
    23400,  # 07 — 3-word rhythm
    33400,  # 08 — SHA-256 chars printing
    36100,  # 09 — LOCKED stamp slam
    47400,  # 10 — PASS slam + exit 0
    64500,  # 11 — after :wq, before red sweep
    68100,  # 12 — EXIT 3 full-screen slam
    71000,  # 13 — audit chain phase-2 begins
    75500,  # 14 — BLOCKED link + foot line
    80000,  # 15 — inventory line reveals
    84500,  # 16 — tagline "Lock the claim before the data."
    88200,  # 17 — sub "Or it didn't happen."
]

# (freq_hz, dur_s, volume, delay_ms, comment)
FAX_CHIRPS = [(1200, 0.04, 0.22, t, "yaml-print") for t in (28500, 28780, 29060, 29340, 29620, 29700)]
BACKSPACES = [(800, 0.025, 0.18, t, "bspc") for t in (60000, 60100, 60200, 60300)]
# Typewriter clicks for sc04 SHA-256 (28 chars), 40ms apart, starting 33500
TYPEWRITER = [(1500, 0.015, 0.12, 33500 + 40 * i, f"tw{i}") for i in range(28)]

OTHER_SFX = [
    (400,  0.25, 0.20,  4500, "strike_whoosh"),   # sc01 tear
    (90,   0.12, 0.42,  4900, "numswap_thud"),    # sc01 71 wipe-in
    (80,   0.14, 0.45, 36000, "locked_slam"),     # sc04 LOCKED
    (100,  0.16, 0.35, 47500, "pass_slam"),       # sc05 PASS
    (600,  0.30, 0.16, 65000, "red_sweep"),       # sc06
    (60,   0.22, 0.55, 68000, "exit3_low"),       # sc06 EXIT 3
    (200,  0.18, 0.35, 68000, "exit3_mid"),       # sc06 EXIT 3
    (2000, 0.06, 0.12, 88700, "chip_settle"),     # sc07 honesty chip
]


def build() -> None:
    assert len(BEATS_MS) == 17
    OUT.parent.mkdir(parents=True, exist_ok=True)

    inputs: list[str] = []
    filters: list[str] = []
    amix_labels: list[str] = []

    # 17 VO inputs
    for i, ms in enumerate(BEATS_MS, start=1):
        p = VO_DIR / f"line_{i:02d}.mp3"
        assert p.exists(), f"missing {p}"
        inputs += ["-i", str(p)]

    # pink-noise bed
    inputs += ["-f", "lavfi", "-t", "90", "-i", "anoisesrc=d=90:c=pink:a=0.02:r=48000"]

    sfx_list = [("fax", f, d, v, t) for (f, d, v, t, _) in FAX_CHIRPS]
    sfx_list += [("bspc", f, d, v, t) for (f, d, v, t, _) in BACKSPACES]
    sfx_list += [("tw", f, d, v, t) for (f, d, v, t, _) in TYPEWRITER]
    sfx_list += [("sfx", f, d, v, t) for (f, d, v, t, _) in OTHER_SFX]

    sfx_start_idx = 18
    for _, f, d, _, _ in sfx_list:
        inputs += ["-f", "lavfi", "-t", f"{d}", "-i", f"sine=f={f}:sample_rate=48000"]

    # VO filters — gentle limiting, slight lowpass to tame ElevenLabs hiss
    for i, ms in enumerate(BEATS_MS, start=1):
        lbl = f"v{i}"
        filters.append(
            f"[{i-1}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"volume=1.0,adelay={ms}|{ms}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Pink bed
    filters.append(
        "[17:a]aformat=channel_layouts=stereo:sample_rates=48000,"
        "lowpass=f=350,volume=0.04[bed]"
    )
    amix_labels.append("bed")

    # SFX — fade envelope + volume + delay
    for n, (_name, f, d, v, t) in enumerate(sfx_list, start=1):
        idx = sfx_start_idx + (n - 1)
        fade_out_start = max(d - 0.005, 0.002)
        lbl = f"sfx{n}"
        filters.append(
            f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d=0.003,afade=t=out:st={fade_out_start}:d=0.005,"
            f"volume={v},adelay={t}|{t}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Mix + master chain
    mix_in = "".join(f"[{l}]" for l in amix_labels)
    n = len(amix_labels)
    filters.append(
        f"{mix_in}amix=inputs={n}:normalize=0:duration=longest[mixed];"
        f"[mixed]alimiter=limit=0.92,loudnorm=I=-15:TP=-1:LRA=10[out]"
    )

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-ac", "2", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-t", "90",
        str(OUT),
    ]
    print(f"amix streams: {n} (VO=17, bed=1, SFX={len(sfx_list)})")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-4000:])
        sys.exit(r.returncode)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
