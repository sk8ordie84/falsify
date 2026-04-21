"""Tests for `falsify replay` — deterministic re-execution verifier."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"


# Tiny deterministic metric: counts non-empty lines in dataset.csv at the
# repo root. Returns (count, count). Stored at csv_metric.py in the
# tmpdir so that `metric_fn: csv_metric:row_count` is importable.
METRIC_SOURCE = textwrap.dedent(
    """\
    from pathlib import Path

    def row_count(_run_dir):
        text = Path("dataset.csv").read_text()
        n = sum(1 for line in text.splitlines() if line.strip())
        return float(n), n
    """
)

DATASET_3_ROWS = "a\nb\nc\n"
DATASET_5_ROWS = "a\nb\nc\nd\ne\n"


def _spec(direction: str, threshold: float) -> str:
    return textwrap.dedent(
        f"""\
        claim: "row count check"
        falsification:
          failure_criteria:
            - metric: rows
              direction: {direction}
              threshold: {threshold}
          minimum_sample_size: 1
          stopping_rule: "one read"
        experiment:
          command: "echo replay-fixture"
          metric_fn: "csv_metric:row_count"
        """
    )


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class ReplayCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        (self.cwd / "csv_metric.py").write_text(METRIC_SOURCE)
        (self.cwd / "dataset.csv").write_text(DATASET_3_ROWS)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _full_cycle(
        self, name: str, *, direction: str = "above", threshold: float = 0.0,
    ) -> str:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(_spec(direction, threshold))
        for cmd in (["lock", name], ["run", name], ["verdict", name]):
            r = _run(cmd, cwd=self.cwd)
            # verdict may exit 10 for FAIL — that's OK, we still want
            # the snapshot written.
            self.assertIn(r.returncode, (0, 10), msg=r.stderr)
        runs_dir = claim_dir / "runs"
        run_ids = sorted(p.name for p in runs_dir.iterdir() if p.is_dir())
        self.assertEqual(len(run_ids), 1)
        return run_ids[-1]

    def test_replay_ok_pass_claim(self) -> None:
        run_id = self._full_cycle("rows-pass", direction="above", threshold=0.0)
        result = _run(["replay", run_id], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("REPLAY OK", result.stdout)

    def test_replay_ok_fail_claim(self) -> None:
        # 3 rows, threshold 100, direction above → FAIL verdict, but
        # the metric value (3.0) is still deterministically reproducible.
        run_id = self._full_cycle(
            "rows-fail", direction="above", threshold=100.0,
        )
        result = _run(["replay", run_id], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("REPLAY OK", result.stdout)

    def test_replay_mismatch_when_dataset_mutated(self) -> None:
        run_id = self._full_cycle(
            "rows-mut", direction="above", threshold=0.0,
        )
        # Swap the dataset under the metric's feet.
        (self.cwd / "dataset.csv").write_text(DATASET_5_ROWS)
        result = _run(["replay", run_id], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        self.assertIn("REPLAY MISMATCH", result.stdout)

    def test_replay_stale_when_spec_changed(self) -> None:
        run_id = self._full_cycle(
            "rows-stale", direction="above", threshold=0.0,
        )
        spec_path = self.cwd / ".falsify" / "rows-stale" / "spec.yaml"
        spec_path.write_text(_spec("above", 999.0))
        relock = _run(["lock", "rows-stale", "--force"], cwd=self.cwd)
        self.assertEqual(relock.returncode, 0, msg=relock.stderr)

        result = _run(["replay", run_id], cwd=self.cwd)
        self.assertEqual(result.returncode, 3, msg=result.stdout + result.stderr)
        self.assertIn("spec changed", result.stderr.lower())

    def test_replay_run_not_found(self) -> None:
        result = _run(["replay", "20990101T000000_000000Z"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("not found", result.stderr)

    def test_replay_tolerance_accepts_float_noise(self) -> None:
        run_id = self._full_cycle(
            "rows-tol", direction="above", threshold=0.0,
        )
        # Inject a tiny delta into the stored snapshot so the
        # re-executed metric (3.0) sits 1e-12 above stored (~3.0 - 1e-12).
        snap_path = (
            self.cwd / ".falsify" / "rows-tol" / "runs" / run_id / "verdict.json"
        )
        snap = json.loads(snap_path.read_text())
        snap["observed_value"] = 3.0 - 1e-12
        snap_path.write_text(json.dumps(snap, indent=2, sort_keys=True))

        result = _run(
            ["replay", run_id, "--tolerance", "1e-9"], cwd=self.cwd
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("REPLAY OK", result.stdout)

    def test_replay_tolerance_rejects_above_threshold(self) -> None:
        run_id = self._full_cycle(
            "rows-tolfail", direction="above", threshold=0.0,
        )
        snap_path = (
            self.cwd / ".falsify" / "rows-tolfail" / "runs" / run_id / "verdict.json"
        )
        snap = json.loads(snap_path.read_text())
        snap["observed_value"] = 3.0 - 1e-6  # delta = 1e-6 > 1e-9
        snap_path.write_text(json.dumps(snap, indent=2, sort_keys=True))

        result = _run(
            ["replay", run_id, "--tolerance", "1e-9"], cwd=self.cwd
        )
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        self.assertIn("REPLAY MISMATCH", result.stdout)

    def test_replay_json_output(self) -> None:
        run_id = self._full_cycle(
            "rows-json", direction="above", threshold=0.0,
        )
        result = _run(["replay", run_id, "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        for key in ("status", "claim", "run_id", "stored", "replayed", "delta"):
            self.assertIn(key, payload)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["claim"], "rows-json")


if __name__ == "__main__":
    unittest.main()
