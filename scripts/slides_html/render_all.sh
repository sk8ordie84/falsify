#!/usr/bin/env bash
# Render all falsify demo scenes to 1920x1080 PNGs via headless Chrome.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

CHROME="${CHROME:-}"
if [ -z "$CHROME" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           "$(command -v google-chrome || true)" \
           "$(command -v chromium || true)"; do
    if [ -n "$c" ] && [ -x "$c" ]; then CHROME="$c"; break; fi
  done
fi
[ -n "$CHROME" ] || { echo "Chrome not found. Set CHROME=..." >&2; exit 1; }

for f in 01_hook.html 02_reveal.html 03_promise.html 04_lock.html 05_tamper.html 06_compose.html 07_close.html; do
  out="${f%.html}.png"
  echo "rendering $f -> $out"
  "$CHROME" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
            --virtual-time-budget=3000 \
            --screenshot="$DIR/$out" --window-size=1920,1080 "file://$DIR/$f" >/dev/null 2>&1
done
echo "done. 7 PNGs in $DIR"
