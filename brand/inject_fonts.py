#!/usr/bin/env python3
"""
falsify brand-v2 — font injection script
Downloads Space Grotesk 700 + JetBrains Mono 400 and injects them as
base64 data URIs into every SVG under brand-v2/.

Run from the repo root:
    python3 brand-v2/inject_fonts.py

Requirements: Python 3.7+, curl (already on macOS)
"""

import os
import base64
import subprocess
import re
from pathlib import Path

BASE = Path(__file__).parent

FONTS = {
    "space_grotesk_bold": {
        "url": "https://github.com/floriankarsten/space-grotesk/raw/master/fonts/otf/SpaceGrotesk-Bold.otf",
        "file": BASE / "_fonts/SpaceGrotesk-Bold.otf",
        "format": "opentype",
        "mime": "font/otf",
        "css_family": "Space Grotesk",
        "css_weight": "700",
    },
    "jetbrains_mono_regular": {
        "url": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/webfonts/JetBrainsMono-Regular.woff2",
        "file": BASE / "_fonts/JetBrainsMono-Regular.woff2",
        "format": "woff2",
        "mime": "font/woff2",
        "css_family": "JetBrains Mono",
        "css_weight": "400",
    },
}


def download_font(name, font):
    font["file"].parent.mkdir(parents=True, exist_ok=True)
    if font["file"].exists():
        print(f"  [cache] {name}")
        return
    print(f"  [dl]    {name}  ←  {font['url']}")
    subprocess.run(
        ["curl", "-fsSL", font["url"], "-o", str(font["file"])],
        check=True,
    )
    print(f"  [ok]    {name}")


def font_b64(font):
    data = font["file"].read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{font['mime']};base64,{b64}"


def make_font_face(font, data_uri):
    return (
        f'@font-face {{ font-family: "{font["css_family"]}"; '
        f'font-weight: {font["css_weight"]}; '
        f'src: url({data_uri}) format("{font["format"]}"); }}'
    )


def inject_into_svg(svg_path, font_rules):
    text = svg_path.read_text(encoding="utf-8")

    # Remove existing @import google fonts lines
    text = re.sub(r"@import url\([^)]*googleapis[^)]*\);\s*\n?", "", text)
    # Remove existing @font-face blocks (we'll replace)
    text = re.sub(
        r"@font-face\s*\{[^}]*\}\s*\n?", "", text, flags=re.DOTALL
    )
    # Remove existing relative src refs
    text = re.sub(r'src: url\("[^"]*_fonts[^"]*"\)[^;]*;', "", text)

    # Find <style> block and inject font-faces at the top
    style_open = text.find("<style>")
    if style_open == -1:
        # No style block — add defs
        insert_pos = text.find(">", text.find("<svg")) + 1
        font_css = "\n".join(font_rules)
        defs_block = f"\n<defs><style>{font_css}</style></defs>"
        text = text[:insert_pos] + defs_block + text[insert_pos:]
    else:
        # Inject after <style>
        inject_pos = style_open + len("<style>")
        font_css = "\n    " + "\n    ".join(font_rules) + "\n    "
        text = text[:inject_pos] + font_css + text[inject_pos:]

    svg_path.write_text(text, encoding="utf-8")
    print(f"  [inject] {svg_path.relative_to(BASE)}")


def main():
    print("falsify brand-v2 — font injection")
    print("=" * 50)

    # 1. Download fonts
    print("\nDownloading fonts...")
    for name, font in FONTS.items():
        download_font(name, font)

    # 2. Generate data URIs
    print("\nEncoding fonts to base64...")
    font_rules = []
    for name, font in FONTS.items():
        uri = font_b64(font)
        rule = make_font_face(font, uri)
        font_rules.append(rule)
        size_kb = len(uri) * 3 / 4 / 1024
        print(f"  {name}: {size_kb:.0f} KB encoded")

    # 3. Inject into all SVGs
    print("\nInjecting into SVGs...")
    svgs = list(BASE.rglob("*.svg"))
    for svg_path in sorted(svgs):
        inject_into_svg(svg_path, font_rules)

    print(f"\nDone. Injected fonts into {len(svgs)} SVG files.")
    print("Open brand-v2/preview.html in Chrome to verify.")


if __name__ == "__main__":
    main()
