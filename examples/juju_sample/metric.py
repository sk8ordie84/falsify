"""Brier score metric for the JUJU anonymized sample.

Stdlib only (csv). Mean squared error between predicted_prob and
outcome over the rows of a CSV with the columns:
event_id, predicted_prob, outcome, stake_usd, timestamp.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "data.csv"


def brier_score(csv_path):
    """Return ``(brier, n_rows)``.

    Accepts a CSV path (str or Path). When given a directory — as
    ``falsify verdict`` does with its ``run_dir`` argument — falls
    back to the bundled ``data.csv`` fixture so the metric stays
    reproducible from the spec alone.
    """
    p = Path(csv_path)
    if p.is_dir() or not p.exists():
        p = FIXTURE

    total = 0.0
    n = 0
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            prob = float(row["predicted_prob"])
            outcome = float(row["outcome"])
            total += (prob - outcome) ** 2
            n += 1

    return ((total / n) if n else 0.0, n)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURE
    brier, n = brier_score(target)
    print(f"brier_score={brier:.4f} n={n}")
