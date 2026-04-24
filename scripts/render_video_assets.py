#!/usr/bin/env python3
"""
render_video_assets.py — Falsify Hackathon Demo · Video Asset Render Pipeline

Usage:
    python3 scripts/render_video_assets.py radar-hero
    python3 scripts/render_video_assets.py radar-mini
    python3 scripts/render_video_assets.py scene 01        (01-07)
    python3 scripts/render_video_assets.py scene all
    python3 scripts/render_video_assets.py all
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

# ── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
OUT_DIR     = REPO_ROOT / "docs" / "assets" / "v2"
FRAMES_ROOT = REPO_ROOT / "docs" / "assets" / "v2" / "_frames"

# HTML sources
RADAR_HTML  = SCRIPTS_DIR / "radar" / "claim-radar.html"
SLIDES_DIR  = SCRIPTS_DIR / "slides_html"

# Chromium headless shell
CHROMIUM_PATH = (
    Path.home()
    / "Library/Caches/ms-playwright/chromium_headless_shell-1208"
    / "chrome-headless-shell-mac-arm64"
    / "chrome-headless-shell"
)

# ── Scene config ─────────────────────────────────────────────────────────────

SCENE_DURATIONS = {
    "01": 11,   # hook — extended for "radiologist" beat
    "02":  7,
    "03": 10,
    "04": 14,
    "05": 16,
    "06": 20,
    "07": 12,
}

FPS = 30

# ── Helpers ──────────────────────────────────────────────────────────────────

def log(asset: str, frame: int, total: int, start: float):
    pct = int(frame / total * 100)
    elapsed = time.monotonic() - start
    print(f"[{asset}] {frame:04d}/{total:04d} ({pct:3d}%)  {elapsed:.1f}s", flush=True)


def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ffmpeg ERROR]\n{result.stderr[-2000:]}", file=sys.stderr)
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])}")


def keep_bookend_frames(frames_dir: Path, name: str, total: int) -> None:
    """Copy first and last PNG out of the frames dir before cleanup."""
    first = frames_dir / "0000.png"
    last  = frames_dir / f"{total - 1:04d}.png"
    if first.exists():
        shutil.copy(first, OUT_DIR / f"{name}_first.png")
    if last.exists():
        shutil.copy(last,  OUT_DIR / f"{name}_last.png")


def encode_mp4(frames_dir: Path, out_path: Path) -> None:
    run_ffmpeg([
        "-framerate", str(FPS),
        "-i", str(frames_dir / "%04d.png"),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ])


def encode_webm_alpha(frames_dir: Path, out_path: Path) -> bool:
    """Attempt VP9 alpha WebM. Returns True on success, False on failure."""
    try:
        run_ffmpeg([
            "-framerate", str(FPS),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-b:v", "0",
            "-crf", "30",
            str(out_path),
        ])
        return True
    except RuntimeError as e:
        print(f"[radar-mini] Alpha WebM failed: {e}. Falling back to MP4 on void-black.", flush=True)
        return False


# ── Radar renderer ───────────────────────────────────────────────────────────

async def render_radar(mode: str) -> None:
    """
    mode: 'hero'  → 1920×1080, 240 frames, output radar_hero.mp4
    mode: 'mini'  → 360×360, 120 frames (one rotation chunk), output radar_mini.webm
                    Falls back to radar_mini.mp4 if alpha encode fails.
    """
    is_hero    = mode == "hero"
    w, h       = (1920, 1080) if is_hero else (360, 360)
    total_frames = 240 if is_hero else 120
    asset_name   = f"radar_{mode}"
    frames_dir   = FRAMES_ROOT / asset_name

    frames_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    url = f"file://{RADAR_HTML}?mode={mode}"
    clip = {"x": 0, "y": 0, "width": w, "height": h}

    wall_start = time.monotonic()
    print(f"[{asset_name}] Starting render — {total_frames} frames at {w}x{h}", flush=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=str(CHROMIUM_PATH),
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.new_page(viewport={"width": w, "height": h})
        await page.goto(url)
        await page.wait_for_function("window.__READY__ === true", timeout=15000)

        for f in range(total_frames):
            frame_path = frames_dir / f"{f:04d}.png"
            await page.evaluate(f"() => window.__SEEK__({f})")
            await page.screenshot(
                path=str(frame_path),
                clip=clip,
                omit_background=(mode == "mini"),
            )
            if f % 30 == 0 or f == total_frames - 1:
                log(asset_name, f + 1, total_frames, wall_start)

        await browser.close()

    print(f"[{asset_name}] Frames done in {time.monotonic() - wall_start:.1f}s. Encoding...", flush=True)

    keep_bookend_frames(frames_dir, asset_name, total_frames)

    fallback_note = ""
    if is_hero:
        out_path = OUT_DIR / "radar_hero.mp4"
        encode_mp4(frames_dir, out_path)
    else:
        webm_path = OUT_DIR / "radar_mini.webm"
        success   = encode_webm_alpha(frames_dir, webm_path)
        if not success:
            if webm_path.exists():
                webm_path.unlink()
            out_path = OUT_DIR / "radar_mini.mp4"
            encode_mp4(frames_dir, out_path)
            fallback_note = "FALLBACK: alpha WebM encode failed; radar_mini encoded as MP4 on void-black."
            print(f"[radar-mini] {fallback_note}", flush=True)
        else:
            out_path = webm_path

    # Cleanup frames
    shutil.rmtree(frames_dir)

    elapsed = time.monotonic() - wall_start
    print(f"[{asset_name}] Done — {out_path.name}  ({elapsed:.1f}s wall-clock)", flush=True)
    if fallback_note:
        # Write fallback note alongside manifest data for later
        note_path = OUT_DIR / "radar_mini_fallback.txt"
        note_path.write_text(fallback_note + "\n")


# ── Scene renderer ───────────────────────────────────────────────────────────

async def render_scene(scene_id: str) -> None:
    """
    scene_id: '01' through '07'
    Frame-accurate capture using WAAPI per-frame seeking. Animations are paused
    immediately after __READY__ fires; we then set each Animation.currentTime
    explicitly for every frame and screenshot. CPU-speed-independent.
    """
    duration_sec = SCENE_DURATIONS[scene_id]
    total_frames = duration_sec * FPS
    asset_name   = f"scene_{scene_id}"
    frames_dir   = FRAMES_ROOT / asset_name

    matches = list(SLIDES_DIR.glob(f"{scene_id}_*.html"))
    if not matches:
        raise FileNotFoundError(f"No HTML found for scene {scene_id} in {SLIDES_DIR}")
    html_file = matches[0]

    frames_dir.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    url        = f"file://{html_file}"
    wall_start = time.monotonic()

    print(f"[{asset_name}] Starting render — {duration_sec}s, {total_frames} frames (seek-mode) — {html_file.name}", flush=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=str(CHROMIUM_PATH),
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(url)
        await page.wait_for_function("window.__READY__ === true", timeout=15000)

        # Pause all animations at t=0 and install a seek helper. The helper also
        # calls window.__PAGE_SEEK__(t_ms) if the page defines one — this lets
        # canvas-based scenes (e.g. sc01 with radar) participate in seek-mode.
        await page.evaluate(
            """() => {
                window.__seekAnims = () => Array.from(document.getAnimations());
                window.__seekAnims().forEach(a => {
                    try { a.pause(); a.currentTime = 0; } catch(e) {}
                });
                window.__SEEK = (t) => {
                    Array.from(document.getAnimations()).forEach(a => {
                        try { a.currentTime = t; } catch(e) {}
                    });
                    if (typeof window.__PAGE_SEEK__ === 'function') {
                        try { window.__PAGE_SEEK__(t); } catch(e) {}
                    }
                };
            }"""
        )

        for frame in range(total_frames):
            t_ms = frame * (1000.0 / FPS)
            await page.evaluate("(t) => window.__SEEK(t)", t_ms)
            frame_path = frames_dir / f"{frame:04d}.png"
            await page.screenshot(path=str(frame_path))
            if frame % 30 == 0 or frame == total_frames - 1:
                log(asset_name, frame + 1, total_frames, wall_start)

        await browser.close()

    actual_frames = total_frames
    print(
        f"[{asset_name}] Captured {actual_frames} frames "
        f"(target {total_frames}) in {time.monotonic() - wall_start:.1f}s. Encoding...",
        flush=True,
    )

    keep_bookend_frames(frames_dir, asset_name, actual_frames)

    out_path = OUT_DIR / f"{asset_name}.mp4"
    encode_mp4(frames_dir, out_path)

    shutil.rmtree(frames_dir)

    elapsed = time.monotonic() - wall_start
    print(f"[{asset_name}] Done — {out_path.name}  ({elapsed:.1f}s wall-clock)", flush=True)


# ── Manifest writer ───────────────────────────────────────────────────────────

def write_manifest() -> None:
    out = OUT_DIR
    manifest_path = out / "MANIFEST.md"

    lines = [
        "# docs/assets/v2 — Render Manifest",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "",
        "## File Tree",
        "",
        "```",
    ]

    mp4_files  = sorted(out.glob("*.mp4"))
    webm_files = sorted(out.glob("*.webm"))
    png_files  = sorted(out.glob("*.png"))

    all_files = mp4_files + webm_files + png_files

    total_bytes = 0
    probe_rows  = []
    warnings    = []

    for f in all_files:
        sz = f.stat().st_size
        total_bytes += sz
        lines.append(f"  {f.name}  ({sz / 1024 / 1024:.2f} MB)")

        if f.suffix in (".mp4", ".webm"):
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(f),
                ],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                import json
                data     = json.loads(result.stdout)
                fmt      = data.get("format", {})
                duration = float(fmt.get("duration", 0))
                bitrate  = int(fmt.get("bit_rate", 0)) // 1000
                probe_rows.append((f.name, f"{duration:.2f}s", f"{bitrate} kbps", f"{sz / 1024 / 1024:.2f} MB"))

    lines.append("```")
    lines.append("")

    # Fallback notes
    fallback_note_path = out / "radar_mini_fallback.txt"
    if fallback_note_path.exists():
        warnings.append(fallback_note_path.read_text().strip())

    # Probe table
    if probe_rows:
        lines += [
            "## Duration & Bitrate (ffprobe)",
            "",
            "| File | Duration | Bitrate | Size |",
            "|------|----------|---------|------|",
        ]
        for row in probe_rows:
            lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
        lines.append("")

    lines += [
        f"## Total Size",
        "",
        f"{total_bytes / 1024 / 1024:.2f} MB across {len(all_files)} files",
        "",
    ]

    if warnings:
        lines += ["## Warnings", ""]
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    manifest_path.write_text("\n".join(lines) + "\n")
    print(f"[manifest] Written to {manifest_path}", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="Falsify hackathon video asset renderer")
    parser.add_argument(
        "target",
        choices=["radar-hero", "radar-mini", "scene", "all"],
        help="What to render",
    )
    parser.add_argument(
        "scene_id",
        nargs="?",
        help="Scene ID (01-07) or 'all', required when target=scene",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_ROOT.mkdir(parents=True, exist_ok=True)

    grand_start = time.monotonic()

    if args.target == "radar-hero":
        await render_radar("hero")

    elif args.target == "radar-mini":
        await render_radar("mini")

    elif args.target == "scene":
        if not args.scene_id:
            parser.error("scene requires a scene_id (01-07 or all)")
        if args.scene_id == "all":
            for sid in SCENE_DURATIONS:
                await render_scene(sid)
        else:
            sid = args.scene_id.zfill(2)
            if sid not in SCENE_DURATIONS:
                parser.error(f"Unknown scene id: {sid}. Valid: {list(SCENE_DURATIONS.keys())}")
            await render_scene(sid)

    elif args.target == "all":
        await render_radar("hero")
        await render_radar("mini")
        for sid in SCENE_DURATIONS:
            await render_scene(sid)

    write_manifest()

    total_elapsed = time.monotonic() - grand_start
    print(f"\nTotal wall-clock: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
