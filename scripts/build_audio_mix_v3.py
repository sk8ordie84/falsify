#!/usr/bin/env python3
"""v3 beat-aligned audio mix: 17 VO lines + pink bed + expanded SFX per HANDOFF."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

VO_DIR = Path("docs/assets/vo_lines")
OUT = Path("docs/assets/v2/_build/audio_v3.m4a")

BEATS_MS = [500, 3000, 5500, 11500, 14500, 18500, 22000, 28000, 32200,
            36000, 42400, 45000, 52000, 60000, 68000, 78000, 82200]

# (freq_hz, dur_s, volume, delay_ms)  — from HANDOFF §SFX bed
FAX_CHIRPS = [(1200, 0.04, 0.25, t) for t in (28500, 28780, 29060, 29340, 29620, 29900)]
BACKSPACES = [(800, 0.02, 0.20, t) for t in (72000, 72100, 72200, 72300)]
# typewriter 28 chars for sc04 hash: start 33500ms, 40ms apart
TYPEWRITER = [(1500, 0.015, 0.15, 33500 + 40 * i) for i in range(28)]

OTHER_SFX = [
    (80,   0.12, 0.35, 32200, "locked_slam"),
    (100,  0.15, 0.30, 41500, "pass_slam"),
    (600,  0.30, 0.18, 42400, "red_sweep"),
    (60,   0.22, 0.55, 45000, "exit3_low"),
    (200,  0.18, 0.35, 45000, "exit3_mid"),
    (400,  0.20, 0.22,  5500, "strike_whoosh"),
    (90,   0.10, 0.40,  6000, "numswap_thud"),
    (2000, 0.06, 0.10, 82200, "chip_settle"),
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

    # pink-noise bed at index 17
    inputs += ["-f", "lavfi", "-t", "90", "-i", "anoisesrc=d=90:c=pink:a=0.02:r=48000"]

    # Collect SFX: fax + backspace + typewriter + other
    sfx_list = []
    for freq, dur, vol, delay in FAX_CHIRPS:
        sfx_list.append(("fax", freq, dur, vol, delay))
    for freq, dur, vol, delay in BACKSPACES:
        sfx_list.append(("bsp", freq, dur, vol, delay))
    for freq, dur, vol, delay in TYPEWRITER:
        sfx_list.append(("tw", freq, dur, vol, delay))
    for freq, dur, vol, delay, name in OTHER_SFX:
        sfx_list.append((name, freq, dur, vol, delay))

    sfx_start_idx = 18
    for _, freq, dur, _, _ in sfx_list:
        inputs += ["-f", "lavfi", "-t", f"{dur}", "-i", f"sine=f={freq}:sample_rate=48000"]

    # VO filters
    for i, ms in enumerate(BEATS_MS, start=1):
        lbl = f"v{i}"
        filters.append(
            f"[{i-1}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"adelay={ms}|{ms}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Bed
    filters.append(
        "[17:a]aformat=channel_layouts=stereo:sample_rates=48000,"
        "lowpass=f=350,volume=0.04[bed]"
    )
    amix_labels.append("bed")

    # SFX
    for n, (name, freq, dur, vol, delay) in enumerate(sfx_list, start=1):
        idx = sfx_start_idx + (n - 1)
        fade_out = max(dur - 0.005, 0.002)
        lbl = f"sfx{n}"
        filters.append(
            f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d=0.003,afade=t=out:st={fade_out}:d=0.005,"
            f"volume={vol},adelay={delay}|{delay}[{lbl}]"
        )
        amix_labels.append(lbl)

    # Final amix + limiter + loudnorm
    mix_in = "".join(f"[{l}]" for l in amix_labels)
    n = len(amix_labels)
    filters.append(
        f"{mix_in}amix=inputs={n}:normalize=0:duration=longest[mixed];"
        f"[mixed]alimiter=limit=0.89,loudnorm=I=-16:TP=-1:LRA=11[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-ac", "2", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-t", "90",
        str(OUT),
    ]

    print(f"amix streams: {n}  (VO=17, bed=1, SFX={len(sfx_list)})")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:])
        sys.exit(res.returncode)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
