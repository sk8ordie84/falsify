#!/usr/bin/env python3
"""v3.3 audio mix: 17 VO lines (new beats) + pink bed + SFX layer → audio_v3.3.m4a"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

VO_DIR = Path("docs/assets/vo_lines")
OUT = Path("docs/assets/v2/_build/audio_v3.3.m4a")

# v3.3 hybrid script beat table (ms)
BEATS_MS = [
    500,    # 01 sc01 "Production radiology classifier."
    2500,   # 02 sc01 "Ninety-four percent..."
    6000,   # 03 sc01 "The actual number was seventy-one."
    12000,  # 04 sc02 "Nobody lied, exactly."
    14500,  # 05 sc02 "The claim just wasn't written..."
    18500,  # 06 sc03 "That's the problem falsify solves."
    29000,  # 07 sc04 "Before the experiment runs..."
    35000,  # 08 sc04 "The hash is a witness."
    43500,  # 09 sc05 "A real run. Ten thousand samples."
    46200,  # 10 sc05 "threshold was locked at point-nine-four"
    50000,  # 11 sc05 "Point-nine-four-three."
    59000,  # 12 sc06 "Someone changes the threshold after the fact."
    62500,  # 13 sc06 "Drops it low enough to pass."
    65000,  # 14 sc06 "It's a small edit..."
    69500,  # 15 sc06 "Except the hash remembers."
    79000,  # 16 sc07 "Every claim — sealed before the data."
    85500,  # 17 sc07 "Or it didn't happen."
]

# SFX ― (freq_hz, dur_s, volume, delay_ms, label)
# tuned to v3.3 scenes: sc04 compose (29–42), sc05 pass (43–58), sc06 tamper (59–78), sc07 close (79–90)
FAX_CHIRPS = [(1200, 0.04, 0.22, t) for t in (29500, 29780, 30060, 30340, 30620, 30900)]
TYPEWRITER_HASH = [(1500, 0.015, 0.13, 33000 + 40 * i) for i in range(28)]  # sc04 hash type-on
BACKSPACES = [(800, 0.022, 0.22, t) for t in (60200, 60320, 60440, 60560)]  # sc06 tamper keystrokes

OTHER_SFX = [
    (80,   0.14, 0.38, 35500, "locked_slam"),   # right after "hash is a witness"
    (100,  0.15, 0.30, 43000, "pass_slam"),     # sc05 verdict slam
    (600,  0.35, 0.18, 59000, "red_sweep"),     # sc06 tamper sweep in
    (60,   0.22, 0.58, 66500, "exit3_low"),     # sc06 block hit
    (200,  0.18, 0.34, 66500, "exit3_mid"),
    (400,  0.20, 0.20,  6500, "strike_whoosh"), # sc01 "seventy-one" drop
    (90,   0.10, 0.42,  6800, "numswap_thud"),
    (2000, 0.06, 0.10, 86200, "chip_settle"),   # sc07 honesty chip
]


def build() -> None:
    assert len(BEATS_MS) == 17
    OUT.parent.mkdir(parents=True, exist_ok=True)

    inputs, filters, amix_labels = [], [], []

    for i in range(1, 18):
        p = VO_DIR / f"line_{i:02d}.mp3"
        assert p.exists(), f"missing {p}"
        inputs += ["-i", str(p)]

    # pink bed index 17
    inputs += ["-f", "lavfi", "-t", "90", "-i", "anoisesrc=d=90:c=pink:a=0.02:r=48000"]

    sfx_list = []
    for f_, d, v, t in FAX_CHIRPS:       sfx_list.append(("fax", f_, d, v, t))
    for f_, d, v, t in TYPEWRITER_HASH:  sfx_list.append(("tw",  f_, d, v, t))
    for f_, d, v, t in BACKSPACES:       sfx_list.append(("bsp", f_, d, v, t))
    for f_, d, v, t, n in OTHER_SFX:     sfx_list.append((n,     f_, d, v, t))

    sfx_start = 18
    for _, freq, dur, _, _ in sfx_list:
        inputs += ["-f", "lavfi", "-t", f"{dur}", "-i", f"sine=f={freq}:sample_rate=48000"]

    # VO
    for i, ms in enumerate(BEATS_MS, 1):
        lbl = f"v{i}"
        filters.append(
            f"[{i-1}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"highpass=f=95,adelay={ms}|{ms},volume=1.04[{lbl}]"
        )
        amix_labels.append(lbl)

    # Bed (lowpass 350 → warm rumble under)
    filters.append(
        "[17:a]aformat=channel_layouts=stereo:sample_rates=48000,"
        "lowpass=f=350,volume=0.045[bed]"
    )
    amix_labels.append("bed")

    for n, (name, freq, dur, vol, delay) in enumerate(sfx_list, 1):
        idx = sfx_start + (n - 1)
        fade_out = max(dur - 0.005, 0.002)
        lbl = f"sfx{n}"
        filters.append(
            f"[{idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
            f"afade=t=in:st=0:d=0.003,afade=t=out:st={fade_out}:d=0.005,"
            f"volume={vol},adelay={delay}|{delay}[{lbl}]"
        )
        amix_labels.append(lbl)

    mix_in = "".join(f"[{l}]" for l in amix_labels)
    n_total = len(amix_labels)
    filters.append(
        f"{mix_in}amix=inputs={n_total}:normalize=0:duration=longest[mixed];"
        f"[mixed]alimiter=limit=0.89,loudnorm=I=-16:TP=-1:LRA=11[out]"
    )

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-ac", "2", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-t", "90",
        str(OUT),
    ]
    print(f"amix streams: {n_total}  (VO=17, bed=1, SFX={len(sfx_list)})")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:]); sys.exit(res.returncode)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
