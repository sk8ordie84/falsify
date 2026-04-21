"""Example metric function for the hello_claim demo.

Reads the last non-empty line of the run's stdout.txt and parses it as a
float. The sample experiment command just echoes a number, so the metric
round-trips whatever the command printed.
"""

from __future__ import annotations

from pathlib import Path


def accuracy(run_dir: Path) -> float:
    text = (run_dir / "stdout.txt").read_text()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line:
            return float(line)
    raise ValueError(f"no numeric output found in {run_dir / 'stdout.txt'}")
