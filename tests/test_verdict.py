"""Tests for `falsify verdict`."""

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


def _spec(
    *,
    direction: str,
    threshold: float,
    echo: str,
    min_n: int = 1,
    metric_fn: str = "metrics:accuracy",
) -> str:
    return textwrap.dedent(
        f"""\
        claim: "Verdict matrix test."
        falsification:
          failure_criteria:
            - metric: accuracy
              direction: {direction}
              threshold: {threshold}
          minimum_sample_size: {min_n}
          stopping_rule: "one run"
        experiment:
          command: "echo {echo}"
          metric_fn: "{metric_fn}"
        """
    )


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class VerdictCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        # Tests import metric_fn from `metrics.py` at cwd — copy the example.
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_claim(self, name: str, spec_yaml: str) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(spec_yaml)
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        run = _run(["run", name], cwd=self.cwd)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        return claim_dir

    def test_verdict_pass_above(self) -> None:
        self._make_claim(
            "pa", _spec(direction="above", threshold=0.5, echo="0.8")
        )
        result = _run(["verdict", "pa"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("PASS", result.stdout)

        verdict = json.loads(
            (self.cwd / ".falsify" / "pa" / "verdict.json").read_text()
        )
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertEqual(verdict["direction"], "above")
        self.assertEqual(verdict["threshold"], 0.5)
        self.assertAlmostEqual(verdict["observed_value"], 0.8)

    def test_verdict_fail_above(self) -> None:
        self._make_claim(
            "fa", _spec(direction="above", threshold=0.5, echo="0.3")
        )
        result = _run(["verdict", "fa"], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stderr)
        self.assertIn("FAIL", result.stdout)

    def test_verdict_pass_below(self) -> None:
        self._make_claim(
            "pb", _spec(direction="below", threshold=0.5, echo="0.2")
        )
        result = _run(["verdict", "pb"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_verdict_equals_within_epsilon(self) -> None:
        # |0.5000000001 - 0.5| ≈ 1e-10, which is below the 1e-9 epsilon → PASS.
        self._make_claim(
            "eq", _spec(direction="equals", threshold=0.5, echo="0.5000000001")
        )
        result = _run(["verdict", "eq"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_verdict_minimum_sample_size_enforced(self) -> None:
        # A metric_fn that returns (value, n) where n < minimum_sample_size.
        (self.cwd / "small_n_metrics.py").write_text(
            textwrap.dedent(
                """\
                def accuracy(run_dir):
                    return (0.8, 3)
                """
            )
        )
        self._make_claim(
            "mn",
            _spec(
                direction="above",
                threshold=0.5,
                echo="0.8",
                min_n=10,
                metric_fn="small_n_metrics:accuracy",
            ),
        )
        result = _run(["verdict", "mn"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("minimum_sample_size", result.stderr)


if __name__ == "__main__":
    unittest.main()
