#!/usr/bin/env python3
"""Inject dot-grid + scanlines + text-bloom utility CSS and overlay DOM into
scenes 02..07. Idempotent: checks a marker before re-injecting."""
from pathlib import Path

SHARED_CSS = """
  /* ── v3.1 visual polish (injected) ── */
  .grid-bg {
    position: absolute; inset: 0;
    background-image: radial-gradient(circle, rgba(57, 217, 138, 0.06) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 1;
  }
  .scanlines {
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.00) 0px,
      rgba(255, 255, 255, 0.00) 2px,
      rgba(0, 0, 0, 0.06) 3px,
      rgba(0, 0, 0, 0.06) 4px
    );
    pointer-events: none;
    z-index: 50;
  }
  .vignette-frame {
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, transparent 50%, rgba(0, 0, 0, 0.45) 100%);
    pointer-events: none;
    z-index: 49;
  }
  /* Bloom utility classes — apply text-shadow glow matching fg color */
  .bloom-green { text-shadow: 0 0 14px rgba(57, 217, 138, 0.55), 0 0 36px rgba(57, 217, 138, 0.25); }
  .bloom-red   { text-shadow: 0 0 14px rgba(255, 77, 109, 0.60), 0 0 36px rgba(255, 77, 109, 0.25); }
"""

MARKER = "/* ── v3.1 visual polish (injected) ── */"

OVERLAY_DIVS = (
    '  <div class="grid-bg"></div>\n'
    '  <div class="vignette-frame"></div>\n'
    '  <div class="scanlines"></div>\n'
)

SCENES = [
    Path("scripts/slides_html/02_reveal.html"),
    Path("scripts/slides_html/03_promise.html"),
    Path("scripts/slides_html/04_lock.html"),
    Path("scripts/slides_html/05_tamper.html"),
    Path("scripts/slides_html/06_compose.html"),
    Path("scripts/slides_html/07_close.html"),
]


def inject(path: Path) -> None:
    text = path.read_text()
    if MARKER in text:
        print(f"skip (already injected): {path}")
        return

    # 1) Insert SHARED_CSS right before </style>
    if "</style>" not in text:
        print(f"WARN no </style>: {path}")
        return
    text = text.replace("</style>", SHARED_CSS + "\n</style>", 1)

    # 2) Insert overlay divs right after <div class="stage">
    stage_tag = '<div class="stage">'
    if stage_tag not in text:
        print(f"WARN no stage: {path}")
        return
    text = text.replace(stage_tag, stage_tag + "\n" + OVERLAY_DIVS, 1)

    path.write_text(text)
    print(f"injected: {path}")


for p in SCENES:
    assert p.exists(), f"missing {p}"
    inject(p)
