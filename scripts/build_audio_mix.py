#!/usr/bin/env python3
"""Assemble beat-aligned audio mix from 17 VO lines + SFX + pink-noise bed.

Reads durations from ffprobe, writes docs/assets/v2/_build/audio_mixed_v2.m4a.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

VO_DIR = Path("docs/assets/vo_lines")
OUT = Path("docs/assets/v2/_build/audio_mixed_v2.m4a")

# (start_ms, voice_gain)
BEATS = [
    (500, 1.00),   # line_01
    (3000, 1.00),  # line_02
    (5500, 1.00),  # line_03
    (11500, 1.00), # line_04
    (14500, 1.00), # line_05
    (18500, 1.00), # line_06
    (22000, 1.00), # line_07
    (28000, 1.00), # line_08
    (32200, 1.00), # line_09
    (36000, 1.00), # line_10
    (42400, 1.00), # line_11
    (45000, 1.00), # line_12
    (52000, 1.00), # line_13
    (60000, 1.00), # line_14
    (68000, 1.00), # line_15
    (78000, 1.00), # line_16
    (82200, 1.00), # line_17
]

# SFX spec from HANDOFF Appendix
# (freq, duration_s, volume, delay_ms, label)
FAX_CHIRPS = [
    (1200, 0.04, 0.25, t) for t in (28500, 28780, 29060, 29340, 29620, 29900)
]
OTHER_SFX = [
    (80,   0.12, 0.35, 32200, "slam"),
    (600,  0.30, 0.18, 42400, "sweep"),
    (60,   0.22, 0.55, 45000, "ex3lo"),
    (200,  0.18, 0.35, 45000, "ex3mid"),
    (2000, 0.06, 0.10, 82200, "chip"),
]


def build() -> None:
    assert len(BEATS) == 17
    OUT.parent.mkdir(parents=True, exist_ok=True)

    inputs: list[str] = []
    filters: list[str] = []
    amix_labels: list[str] = []

    # 17 VO inputs
    for i, (start_ms, gain) in enumerate(BEATS, start=1):
        path = VO_DIR / f"line_{i:02d}.mp3"
        assert path.exists(), f"missing {path}"
        inputs += ["-i", str(path)]

    # Pink-noise bed input
    bed_idx = 17
    inputs += ["-f", "lavfi", "-t", "90", "-i", "anoisesrc=d=90:c=pink:a=0.02:r=48000"]

    # 6 fax chirps
    fax_start_idx = 18
    for freq, dur, vol, delay in FAX_CHIRPS:
        inputs += ["-f", "lavfi", "-t", f"{dur}", "-i", f"sine=f={freq}:sample_rate=48000"]

    # 5 other SFX
    other_start_idx = fax_start_idx + len(FAX_CHIRPS)  # = 24
    for freq, dur, vol, delay, label in OTHER_SFX:
        inputs += ["-f", "lavfi", "-t", f"{dur}", "-i", f"sine=f={freq}:sample_rate=48000"]

    # Build filter graph — VO
    for i, (start_ms, gain) in enumerate(BEATS, start=1):
        in_idx = i - 1
        lbl = f"v{i}"
        filters.append(
            f"[{in_idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"volume={gain},adelay={start_ms}|{start_ms}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Bed
    filters.append(
        f"[{bed_idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
        f"lowpass=f=350,volume=0.04[bed]"
    )
    amix_labels.append("bed")

    # Fax chirps — short tone with fade envelope
    for n, (freq, dur, vol, delay) in enumerate(FAX_CHIRPS, start=1):
        idx = fax_start_idx + (n - 1)
        lbl = f"fax{n}"
        fade_out = max(dur - 0.01, 0.01)
        filters.append(
            f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d=0.005,afade=t=out:st={fade_out}:d=0.01,"
            f"volume={vol},adelay={delay}|{delay}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Other SFX
    for n, (freq, dur, vol, delay, label) in enumerate(OTHER_SFX, start=1):
        idx = other_start_idx + (n - 1)
        fade_out = max(dur - 0.02, 0.01)
        filters.append(
            f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d=0.01,afade=t=out:st={fade_out}:d=0.02,"
            f"volume={vol},adelay={delay}|{delay}[{label}]"
        )
        amix_labels.append(label)

    # Final amix + limiter + loudnorm
    mix_in = "".join(f"[{l}]" for l in amix_labels)
    n_inputs = len(amix_labels)
    filters.append(
        f"{mix_in}amix=inputs={n_inputs}:normalize=0:duration=longest[mixed];"
        f"[mixed]alimiter=limit=0.89,loudnorm=I=-16:TP=-1:LRA=11[out]"
    )

    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ac", "2", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-t", "90",
        str(OUT),
    ]

    print(f"running ffmpeg with {len(inputs)//2} inputs, {n_inputs} mix streams")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:])
        sys.exit(res.returncode)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
