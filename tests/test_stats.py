"""Tests for `falsify stats`."""

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


def _spec(*, direction: str, threshold: float, echo: str, min_n: int = 1) -> str:
    return textwrap.dedent(
        f"""\
        claim: "stats test"
        falsification:
          failure_criteria:
            - metric: accuracy
              direction: {direction}
              threshold: {threshold}
          minimum_sample_size: {min_n}
          stopping_rule: "once"
        experiment:
          command: "echo {echo}"
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


class StatsCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_claim(
        self,
        name: str,
        *,
        direction: str = "above",
        threshold: float = 0.5,
        echo: str = "0.8",
        min_n: int = 1,
    ) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(
            _spec(direction=direction, threshold=threshold, echo=echo, min_n=min_n)
        )
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        run = _run(["run", name], cwd=self.cwd)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        _run(["verdict", name], cwd=self.cwd)  # may exit 0 (PASS) or 10 (FAIL)

    def test_stats_empty_when_no_falsify_dir(self) -> None:
        result = _run(["stats"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("0 specs", result.stdout)

    def test_stats_lists_locked_specs(self) -> None:
        self._make_claim("alpha", echo="0.8")
        self._make_claim("beta", echo="0.3")

        result = _run(["stats"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("alpha", result.stdout)
        self.assertIn("beta", result.stdout)

    def test_stats_json_mode_is_valid_json(self) -> None:
        self._make_claim("solo", echo="0.8")

        result = _run(["stats", "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "solo")
        self.assertIn("state", data[0])

    def test_stats_filter_by_name(self) -> None:
        self._make_claim("demo-foo", echo="0.8")
        self._make_claim("demo-bar", echo="0.8")

        result = _run(["stats", "--name", "foo"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("demo-foo", result.stdout)
        self.assertNotIn("demo-bar", result.stdout)

    def test_stats_aggregate_counts_correct(self) -> None:
        self._make_claim("ok", echo="0.8", direction="above", threshold=0.5)
        self._make_claim("bad", echo="0.3", direction="above", threshold=0.5)

        result = _run(["stats"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("2 specs: 1 PASS, 1 FAIL", result.stdout)

    def test_stats_exit_code_is_zero_on_mixed_states(self) -> None:
        self._make_claim("ok", echo="0.8", direction="above", threshold=0.5)
        self._make_claim("bad", echo="0.3", direction="above", threshold=0.5)

        result = _run(["stats"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
