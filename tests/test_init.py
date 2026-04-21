"""Tests for `falsify init`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class InitCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_init_creates_spec_from_template(self) -> None:
        result = _run(["init", "my-claim"], cwd=self.cwd)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        spec = self.cwd / ".falsify" / "my-claim" / "spec.yaml"
        self.assertTrue(spec.exists())

        content = spec.read_text()
        self.assertIn("<one-sentence hypothesis", content)
        self.assertIn("TODO: real threshold", content)

    def test_init_fails_when_claim_already_exists(self) -> None:
        first = _run(["init", "dup"], cwd=self.cwd)
        self.assertEqual(first.returncode, 0, msg=first.stderr)

        second = _run(["init", "dup"], cwd=self.cwd)
        self.assertEqual(second.returncode, 1)
        self.assertIn("already exists", second.stderr)


if __name__ == "__main__":
    unittest.main()
