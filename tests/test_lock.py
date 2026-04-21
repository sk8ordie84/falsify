"""Tests for `falsify lock`."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"


VALID_SPEC = textwrap.dedent(
    """\
    claim: "Model accuracy on eval set exceeds 0.85."

    falsification:
      failure_criteria:
        - metric: accuracy
          direction: below
          threshold: 0.85
      minimum_sample_size: 1000
      stopping_rule: "after 1 epoch over eval set"

    experiment:
      command: "python run_eval.py"
      dataset: "data/eval.csv"
      metric_fn: "my_pkg.metrics:accuracy"
    """
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class LockCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_spec(self, name: str, text: str) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True, exist_ok=True)
        spec = claim_dir / "spec.yaml"
        spec.write_text(text)
        return spec

    def test_lock_succeeds_on_valid_spec(self) -> None:
        self._write_spec("good", VALID_SPEC)
        result = _run(["lock", "good"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        lock_path = self.cwd / ".falsify" / "good" / "spec.lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text())
        self.assertEqual(len(lock["spec_hash"]), 64)
        self.assertIn("locked_at", lock)
        self.assertIn("canonical_spec_yaml", lock)
        self.assertIn("accuracy", lock["canonical_spec_yaml"])

    def test_lock_rejects_placeholder_values(self) -> None:
        # `init` leaves the template's placeholders in place.
        init = _run(["init", "fresh"], cwd=self.cwd)
        self.assertEqual(init.returncode, 0, msg=init.stderr)

        result = _run(["lock", "fresh"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("placeholder", result.stderr.lower())
        # Report should point at specific fields.
        self.assertIn("claim", result.stderr)
        self.assertIn("experiment.metric_fn", result.stderr)

    def test_lock_detects_modification_after_lock(self) -> None:
        spec = self._write_spec("modtest", VALID_SPEC)
        first = _run(["lock", "modtest"], cwd=self.cwd)
        self.assertEqual(first.returncode, 0, msg=first.stderr)

        spec.write_text(spec.read_text().replace("0.85", "0.95"))

        second = _run(["lock", "modtest"], cwd=self.cwd)
        self.assertEqual(second.returncode, 3, msg=second.stdout + second.stderr)
        self.assertIn("modified", second.stderr.lower())

        # --force allows relocking.
        forced = _run(["lock", "modtest", "--force"], cwd=self.cwd)
        self.assertEqual(forced.returncode, 0, msg=forced.stderr)

    def test_canonical_hash_is_deterministic(self) -> None:
        # Same logical content, different key order / indentation / quoting.
        spec_a = textwrap.dedent(
            """\
            claim: "Baseline beats random."
            falsification:
              failure_criteria:
                - metric: accuracy
                  direction: below
                  threshold: 0.5
              minimum_sample_size: 100
              stopping_rule: "after 1 epoch"
            experiment:
              command: "python run.py"
              metric_fn: "m.pkg:accuracy"
            """
        )
        spec_b = textwrap.dedent(
            """\
            experiment:
                metric_fn:  "m.pkg:accuracy"
                command:    "python run.py"
            falsification:
                stopping_rule:       "after 1 epoch"
                minimum_sample_size: 100
                failure_criteria:
                    -   direction: below
                        threshold: 0.5
                        metric:    accuracy
            claim: "Baseline beats random."
            """
        )
        self._write_spec("variant-a", spec_a)
        self._write_spec("variant-b", spec_b)

        ra = _run(["lock", "variant-a"], cwd=self.cwd)
        rb = _run(["lock", "variant-b"], cwd=self.cwd)
        self.assertEqual(ra.returncode, 0, msg=ra.stderr)
        self.assertEqual(rb.returncode, 0, msg=rb.stderr)

        hash_a = json.loads(
            (self.cwd / ".falsify" / "variant-a" / "spec.lock.json").read_text()
        )["spec_hash"]
        hash_b = json.loads(
            (self.cwd / ".falsify" / "variant-b" / "spec.lock.json").read_text()
        )["spec_hash"]
        self.assertEqual(hash_a, hash_b)


if __name__ == "__main__":
    unittest.main()
