"""Tests for `falsify run`."""

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


def _spec(command: str) -> str:
    return textwrap.dedent(
        f"""\
        claim: "Smoke run — command exits cleanly."
        falsification:
          failure_criteria:
            - metric: value
              direction: above
              threshold: 0.0
          minimum_sample_size: 1
          stopping_rule: "one run"
        experiment:
          command: {command!r}
          metric_fn: "metrics:value"
        """
    )


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class RunCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _prepare_claim(self, name: str, command: str) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(_spec(command))
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        return claim_dir

    def test_run_succeeds_with_simple_command(self) -> None:
        self._prepare_claim("ok", "echo hello")

        result = _run(["run", "ok"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        run_dirs = list((self.cwd / ".falsify" / "ok" / "runs").iterdir())
        self.assertEqual(len(run_dirs), 1)
        run_dir = run_dirs[0]

        self.assertTrue((run_dir / "stdout.txt").exists())
        self.assertTrue((run_dir / "stderr.txt").exists())
        self.assertTrue((run_dir / "run_meta.json").exists())
        self.assertTrue((run_dir / "spec.lock.json").exists())
        self.assertIn("hello", (run_dir / "stdout.txt").read_text())

        meta = json.loads((run_dir / "run_meta.json").read_text())
        self.assertEqual(meta["returncode"], 0)
        self.assertFalse(meta["timed_out"])
        self.assertIn("python_version", meta)
        self.assertIn("hostname", meta)

        latest = self.cwd / ".falsify" / "ok" / "latest_run"
        self.assertTrue(latest.is_symlink() or latest.is_file())

    def test_run_detects_hash_mismatch(self) -> None:
        claim_dir = self._prepare_claim("mod", "echo hi")

        spec_path = claim_dir / "spec.yaml"
        spec_path.write_text(_spec("echo changed"))

        result = _run(["run", "mod"], cwd=self.cwd)
        self.assertEqual(result.returncode, 3, msg=result.stdout + result.stderr)
        self.assertIn("modified", result.stderr.lower())

    def test_run_exits_1_on_bad_command(self) -> None:
        self._prepare_claim("bad", "false")

        result = _run(["run", "bad"], cwd=self.cwd)
        self.assertEqual(result.returncode, 1, msg=result.stdout + result.stderr)

        run_dirs = list((self.cwd / ".falsify" / "bad" / "runs").iterdir())
        self.assertEqual(len(run_dirs), 1)
        meta = json.loads((run_dirs[0] / "run_meta.json").read_text())
        self.assertEqual(meta["returncode"], 1)


if __name__ == "__main__":
    unittest.main()
