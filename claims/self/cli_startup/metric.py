"""CLI startup latency: median wall-time of `python3 falsify.py --help`.

Stdlib only. Spawns the help command five times from the repo root
and returns the median elapsed milliseconds.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FALSIFY_PY = REPO_ROOT / "falsify.py"
SAMPLES = 5


def cli_startup_ms(_run_dir) -> tuple[float, int]:
    """Return (median_ms, 5). Subprocess failures are not retried."""
    timings_ms: list[float] = []
    for _ in range(SAMPLES):
        start = time.perf_counter()
        subprocess.run(
            [sys.executable, str(FALSIFY_PY), "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        timings_ms.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(timings_ms), SAMPLES


if __name__ == "__main__":
    median_ms, n = cli_startup_ms(None)
    print(f"median_ms={median_ms:.1f} n={n}")
