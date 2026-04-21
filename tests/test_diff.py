"""Tests for `falsify diff`."""

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


SPEC = textwrap.dedent(
    """\
    claim: "diff test"
    falsification:
      failure_criteria:
        - metric: accuracy
          direction: above
          threshold: 0.5
      minimum_sample_size: 1
      stopping_rule: "once"
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


class DiffCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _lock(self, name: str, spec_text: str = SPEC) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        spec_path = claim_dir / "spec.yaml"
        spec_path.write_text(spec_text)
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        return spec_path

    def test_diff_identical_returns_zero(self) -> None:
        self._lock("same")
        result = _run(["diff", "same"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("---", result.stdout)  # no unified-diff header
        self.assertIn("identical", result.stdout)

    def test_diff_threshold_changed_returns_3(self) -> None:
        spec = self._lock("edited")
        spec.write_text(SPEC.replace("0.5", "0.9"))

        result = _run(["diff", "edited"], cwd=self.cwd)
        self.assertEqual(result.returncode, 3, msg=result.stdout + result.stderr)
        self.assertIn("threshold", result.stdout)
        self.assertIn("-    threshold: 0.5", result.stdout)
        self.assertIn("+    threshold: 0.9", result.stdout)

    def test_diff_shows_both_hashes(self) -> None:
        spec = self._lock("twohash")
        locked = json.loads(
            (self.cwd / ".falsify" / "twohash" / "spec.lock.json").read_text()
        )
        spec.write_text(SPEC.replace("0.5", "0.9"))

        result = _run(["diff", "twohash"], cwd=self.cwd)
        self.assertEqual(result.returncode, 3, msg=result.stderr)
        # The locked short hash appears on the --- line.
        self.assertIn(locked["spec_hash"][:12], result.stdout)
        # The +++ line carries the current short hash — any 12-hex after "current@".
        self.assertRegex(result.stdout, r"\+\+\+ current@[0-9a-f]{12}")

    def test_diff_file_vs_file_mode(self) -> None:
        a = self.cwd / "a.yaml"
        b = self.cwd / "b.yaml"
        a.write_text("a: 1\nb: 2\n")
        b.write_text("b: 2\na: 3\n")

        result = _run(
            ["diff", "--file-vs-file", str(a), str(b)], cwd=self.cwd
        )
        self.assertEqual(result.returncode, 3, msg=result.stderr)
        self.assertIn("-a: 1", result.stdout)
        self.assertIn("+a: 3", result.stdout)

    def test_diff_missing_spec_returns_2(self) -> None:
        (self.cwd / ".falsify" / "ghost").mkdir(parents=True)
        result = _run(["diff", "ghost"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("not found", result.stderr)

    def test_lock_now_stores_canonical_yaml(self) -> None:
        self._lock("persisted")
        lock = json.loads(
            (self.cwd / ".falsify" / "persisted" / "spec.lock.json").read_text()
        )
        self.assertIn("canonical_yaml", lock)
        self.assertIn("accuracy", lock["canonical_yaml"])

    def test_diff_legacy_lock_flagged(self) -> None:
        claim_dir = self.cwd / ".falsify" / "legacy"
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(SPEC)
        # Hand-craft a lock with NO canonical_yaml and a hash that won't match
        # the current spec — forces the legacy-warning branch.
        (claim_dir / "spec.lock.json").write_text(
            json.dumps(
                {
                    "spec_hash": "deadbeef" + "0" * 56,
                    "locked_at": "2026-01-01T00:00:00+00:00",
                }
            )
        )
        result = _run(["diff", "legacy"], cwd=self.cwd)
        self.assertIn("legacy", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
