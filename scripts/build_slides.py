#!/usr/bin/env python3
"""Render the five demo video text slides to PNG, 884x630, solid #0c0c0c.

Each slide is a single frame; the MP4 loop is done downstream with
`ffmpeg -loop 1 -t <d>`. Keeping the text layout in Python avoids
the drawtext ffmpeg filter, which is not compiled into the brew
ffmpeg on this machine.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("docs/assets")
W, H = 884, 630
BG = (12, 12, 12)              # 0x0c0c0c
PRIMARY = (255, 255, 255)
SECONDARY = (136, 136, 136)    # 0x888888
ACCENT_RED = (255, 77, 77)     # 0xff4d4d
ACCENT_YEL = (255, 200, 87)    # 0xffc857

MENLO_REG = "/System/Library/Fonts/Menlo.ttc"
MENLO_BOLD_IDX = 1             # second face in the collection
HELVETICA = "/System/Library/Fonts/Helvetica.ttc"


def font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size, index=index)


def centered_x(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> int:
    l, _, r, _ = draw.textbbox((0, 0), text, font=f)
    return (W - (r - l)) // 2 - l


def draw_centered(draw, y, text, f, fill):
    draw.text((centered_x(draw, text, f), y), text, font=f, fill=fill)


def new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def slide_1_hook() -> Image.Image:
    """94%  →  71%  with colored segments, subtitle beneath."""
    img, d = new_canvas()
    big = font(MENLO_REG, 140, index=MENLO_BOLD_IDX)
    sub = font(HELVETICA, 22)

    parts = [("94%", PRIMARY), (" ", PRIMARY), ("-->", ACCENT_YEL),
             (" ", PRIMARY), ("71%", ACCENT_RED)]
    widths = []
    for text, _ in parts:
        l, _, r, _ = d.textbbox((0, 0), text, font=big)
        widths.append(r - l)
    total = sum(widths)
    # Vertical centering of the big row.
    _, t, _, b = d.textbbox((0, 0), "94%", font=big)
    row_h = b - t
    y_big = (H - row_h) // 2 - 40

    x = (W - total) // 2
    for (text, color), w in zip(parts, widths):
        d.text((x, y_big), text, font=big, fill=color)
        x += w

    subtitle = "accuracy claim  ·  3 weeks later"
    draw_centered(d, y_big + row_h + 60, subtitle, sub, SECONDARY)
    return img


def slide_2_promise() -> Image.Image:
    img, d = new_canvas()
    big = font(HELVETICA, 48, index=1)  # bold face
    sub = font(HELVETICA, 22)

    line1 = "The claim was never falsifiable."
    line2 = "Nobody locked the metric, the threshold,"
    line3 = "or the dataset before the experiment ran."

    _, t, _, b = d.textbbox((0, 0), line1, font=big)
    h1 = b - t
    _, t, _, b = d.textbbox((0, 0), line2, font=sub)
    h2 = b - t

    block_h = h1 + 40 + h2 + 12 + h2
    y0 = (H - block_h) // 2

    draw_centered(d, y0, line1, big, PRIMARY)
    draw_centered(d, y0 + h1 + 40, line2, sub, SECONDARY)
    draw_centered(d, y0 + h1 + 40 + h2 + 12, line3, sub, SECONDARY)
    return img


def slide_3_title() -> Image.Image:
    img, d = new_canvas()
    small = font(HELVETICA, 20)
    big = font(HELVETICA, 54, index=1)
    sub = font(HELVETICA, 22)

    tagline = "falsify"
    headline = "Lock the claim before the data."
    subtitle = "SHA-256 pre-registration for AI"

    # Top tagline.
    draw_centered(d, 130, tagline, small, SECONDARY)
    # Center headline.
    _, t, _, b = d.textbbox((0, 0), headline, font=big)
    h = b - t
    y = (H - h) // 2
    draw_centered(d, y, headline, big, PRIMARY)
    # Subtitle below.
    draw_centered(d, y + h + 28, subtitle, sub, SECONDARY)
    return img


def slide_4_scale() -> Image.Image:
    img, d = new_canvas()
    small = font(HELVETICA, 20)
    mono = font(MENLO_REG, 28)

    top = "Built with Claude Code"
    center = "5 skills  ·  2 subagents  ·  3 slash commands  ·  1 MCP server"

    draw_centered(d, 140, top, small, SECONDARY)
    _, t, _, b = d.textbbox((0, 0), center, font=mono)
    h = b - t
    y = (H - h) // 2
    draw_centered(d, y, center, mono, PRIMARY)
    return img


def slide_5_end() -> Image.Image:
    img, d = new_canvas()
    big = font(HELVETICA, 44, index=1)
    italic_small = font(HELVETICA, 22, index=2)  # italic face
    url_mono = font(MENLO_REG, 24)

    line1 = "Lock the claim before the data."
    line2 = "Or it didn't happen."
    line3 = "→  github.com/studio-11-co/falsify"

    _, t, _, b = d.textbbox((0, 0), line1, font=big)
    h1 = b - t
    _, t, _, b = d.textbbox((0, 0), line2, font=italic_small)
    h2 = b - t
    _, t, _, b = d.textbbox((0, 0), line3, font=url_mono)
    h3 = b - t

    block_h = h1 + 24 + h2 + 50 + h3
    y0 = (H - block_h) // 2

    draw_centered(d, y0, line1, big, PRIMARY)
    draw_centered(d, y0 + h1 + 24, line2, italic_small, SECONDARY)
    draw_centered(d, y0 + h1 + 24 + h2 + 50, line3, url_mono, ACCENT_YEL)
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slide_1_hook().save(OUT_DIR / "slide_1.png")
    slide_2_promise().save(OUT_DIR / "slide_2.png")
    slide_3_title().save(OUT_DIR / "slide_3.png")
    slide_4_scale().save(OUT_DIR / "slide_4.png")
    slide_5_end().save(OUT_DIR / "slide_5.png")
    for n in range(1, 6):
        p = OUT_DIR / f"slide_{n}.png"
        print(f"wrote {p} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
