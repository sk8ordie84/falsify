#!/usr/bin/env python3
"""
Inject base64-embedded @font-face blocks into every scripts/slides_html/*.html
so Playwright-rendered frames don't fall back to system serifs.

Idempotent — checks for sentinel marker before injecting.
"""
import base64
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FONTS_DIR = Path(__file__).parent / "_fonts"
SCENES_DIR = REPO / "scripts" / "slides_html"
SENTINEL = "/* __FALSIFY_FONTS_EMBEDDED__ */"

SG = FONTS_DIR / "SpaceGrotesk-Bold.otf"
JB = FONTS_DIR / "JetBrainsMono-Regular.woff2"

assert SG.exists(), f"missing {SG}"
assert JB.exists(), f"missing {JB}"

sg_b64 = base64.b64encode(SG.read_bytes()).decode()
jb_b64 = base64.b64encode(JB.read_bytes()).decode()

BLOCK = f"""{SENTINEL}
@font-face {{
  font-family: 'Space Grotesk';
  font-weight: 700;
  font-style: normal;
  font-display: block;
  src: url(data:font/otf;base64,{sg_b64}) format('opentype');
}}
@font-face {{
  font-family: 'Space Grotesk';
  font-weight: 400;
  font-style: normal;
  font-display: block;
  src: url(data:font/otf;base64,{sg_b64}) format('opentype');
}}
@font-face {{
  font-family: 'JetBrains Mono';
  font-weight: 400;
  font-style: normal;
  font-display: block;
  src: url(data:font/woff2;base64,{jb_b64}) format('woff2');
}}
"""

for html in sorted(SCENES_DIR.glob("*.html")):
    text = html.read_text()
    if SENTINEL in text:
        print(f"  [skip] {html.name}  (already embedded)")
        continue
    if "<style>" not in text:
        print(f"  [warn] {html.name}  (no <style>)")
        continue
    text = text.replace("<style>", "<style>\n" + BLOCK, 1)
    html.write_text(text)
    print(f"  [inject] {html.name}")

print("done.")
