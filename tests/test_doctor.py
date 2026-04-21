"""Tests for `falsify doctor`."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
REAL_HOOK = REPO_ROOT / "hooks" / "commit-msg"
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


VALID_SPEC = textwrap.dedent(
    """\
    claim: "doctor test"
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

INVALID_SPEC = textwrap.dedent(
    """\
    falsification:
      failure_criteria:
        - metric: x
          direction: above
          threshold: 0.5
      minimum_sample_size: 1
      stopping_rule: "once"
    experiment:
      command: "echo 0"
      metric_fn: "m:f"
    """
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class DoctorCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.cwd,
            check=True,
            capture_output=True,
        )
        (self.cwd / "hooks").mkdir()
        shutil.copy(REAL_HOOK, self.cwd / "hooks" / "commit-msg")
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_claim(self, name: str, spec_text: str) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(spec_text)
        return claim_dir

    def _full_cycle(self, name: str) -> None:
        self._write_claim(name, VALID_SPEC)
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        run = _run(["run", name], cwd=self.cwd)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        verdict = _run(["verdict", name], cwd=self.cwd)
        self.assertEqual(verdict.returncode, 0, msg=verdict.stderr)

    def test_doctor_clean_env_exits_zero(self) -> None:
        result = _run(["doctor"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("[OK]", result.stdout)
        self.assertIn("Python version", result.stdout)
        self.assertIn("pyyaml importable", result.stdout)

    def test_doctor_bad_spec_exits_two(self) -> None:
        self._write_claim("bad", INVALID_SPEC)
        result = _run(["doctor"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("[FAIL]", result.stdout)
        self.assertIn("bad", result.stdout)

    def test_doctor_stale_run_produces_warn(self) -> None:
        self._full_cycle("stale")
        verdict_path = self.cwd / ".falsify" / "stale" / "verdict.json"
        data = json.loads(verdict_path.read_text())
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        data["checked_at"] = old
        verdict_path.write_text(json.dumps(data, indent=2, sort_keys=True))

        result = _run(["doctor"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("[WARN]", result.stdout)
        self.assertIn("stale", result.stdout.lower())

    def test_doctor_missing_hook_produces_info(self) -> None:
        # setUp does NOT install the hook, so this is the default state.
        result = _run(["doctor"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("[INFO]", result.stdout)
        self.assertIn("hook not installed", result.stdout)

    def test_doctor_json_mode_valid_json(self) -> None:
        result = _run(["doctor", "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("summary", data)
        self.assertIn("checks", data)
        self.assertIsInstance(data["checks"], list)
        for key in ("ok", "warn", "fail", "info"):
            self.assertIn(key, data["summary"])

    def test_doctor_specs_only_skips_env_checks(self) -> None:
        result = _run(["doctor", "--specs-only"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("Python version", result.stdout)
        self.assertNotIn("pyyaml importable", result.stdout)


if __name__ == "__main__":
    unittest.main()
