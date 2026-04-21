"""Tests for `falsify list`."""

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
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "List demo."
    falsification:
      failure_criteria:
        - metric: accuracy
          direction: above
          threshold: 0.5
      minimum_sample_size: 1
      stopping_rule: "one run"
    experiment:
      command: "echo 0.8"
      metric_fn: "metrics:accuracy"
    """
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class ListCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_spec(self, name: str) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True, exist_ok=True)
        (claim_dir / "spec.yaml").write_text(SIMPLE_SPEC)
        return claim_dir

    def test_list_empty_shows_hint(self) -> None:
        result = _run(["list"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("No hypotheses yet", result.stdout)

    def test_list_shows_locked_but_unrun_claim(self) -> None:
        claim_dir = self._write_spec("pending")
        lock = _run(["lock", "pending"], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)

        result = _run(["list"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        hash_prefix = json.loads(
            (claim_dir / "spec.lock.json").read_text()
        )["spec_hash"][:12]
        self.assertIn("pending", result.stdout)
        self.assertIn(hash_prefix, result.stdout)
        # No run yet → last-run and verdict columns hold "-".
        rows = [line for line in result.stdout.splitlines() if "pending" in line]
        self.assertEqual(len(rows), 1)
        pending_row = rows[0]
        # Count dash-only columns: expect 3 ("-" appears as last-run, verdict, observed).
        self.assertGreaterEqual(pending_row.count(" - "), 2)

    def test_list_after_full_cycle_and_json(self) -> None:
        self._write_spec("done")
        for cmd in (["lock", "done"], ["run", "done"], ["verdict", "done"]):
            r = _run(cmd, cwd=self.cwd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)

        table = _run(["list"], cwd=self.cwd)
        self.assertEqual(table.returncode, 0, msg=table.stderr)
        self.assertIn("done", table.stdout)
        self.assertIn("PASS", table.stdout)

        js = _run(["list", "--json"], cwd=self.cwd)
        self.assertEqual(js.returncode, 0, msg=js.stderr)
        data = json.loads(js.stdout)
        self.assertEqual(len(data), 1)
        row = data[0]
        self.assertEqual(row["name"], "done")
        self.assertTrue(row["locked"])
        self.assertEqual(row["verdict"], "PASS")
        self.assertAlmostEqual(row["observed_value"], 0.8)
        self.assertIsNotNone(row["last_run"])


if __name__ == "__main__":
    unittest.main()
