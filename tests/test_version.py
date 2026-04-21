"""Tests for `falsify version` and the `--version` flag."""

from __future__ import annotations

import importlib.util
import json
import re
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


class VersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_version_subcommand_prints_version(self) -> None:
        result = _run(["version"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("0.1.0", result.stdout)
        self.assertIn("falsify", result.stdout)

    def test_version_flag_prints_version(self) -> None:
        result = _run(["--version"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # argparse's `action='version'` writes to stdout on Python 3.11+.
        self.assertIn("0.1.0", result.stdout)

    def test_version_subcommand_json_mode(self) -> None:
        result = _run(["version", "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("version", data)
        self.assertEqual(data["name"], "falsify")
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")

    def test_version_constant_matches_semver(self) -> None:
        spec = importlib.util.spec_from_file_location("falsify_mod", FALSIFY)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertRegex(module.__version__, r"^\d+\.\d+\.\d+$")

    def test_version_exits_zero(self) -> None:
        self.assertEqual(_run(["version"], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["--version"], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["version", "--json"], cwd=self.cwd).returncode, 0)


if __name__ == "__main__":
    unittest.main()
