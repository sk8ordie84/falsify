"""Tests for `falsify hook install` and `falsify hook uninstall`."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
REAL_HOOK_SRC = REPO_ROOT / "hooks" / "commit-msg"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class HookInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        # Minimal git repo.
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.cwd,
            check=True,
            capture_output=True,
        )
        # The install command looks for hooks/commit-msg at the repo root,
        # so copy our real hook in.
        (self.cwd / "hooks").mkdir()
        shutil.copy(REAL_HOOK_SRC, self.cwd / "hooks" / "commit-msg")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _target(self) -> Path:
        return self.cwd / ".git" / "hooks" / "commit-msg"

    def test_install_into_fresh_repo(self) -> None:
        result = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        hook = self._target()
        self.assertTrue(hook.exists())
        self.assertTrue(os.access(hook, os.X_OK))
        self.assertIn("Installed", result.stdout)

    def test_install_backs_up_existing_hook(self) -> None:
        existing = self._target()
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("#!/bin/sh\necho pre-existing\n")
        existing.chmod(0o755)

        result = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        baks = list((self.cwd / ".git" / "hooks").glob("commit-msg.bak.*"))
        self.assertEqual(len(baks), 1, f"expected one .bak, found {baks}")
        self.assertIn("echo pre-existing", baks[0].read_text())

        self.assertEqual(
            existing.read_text(), (self.cwd / "hooks" / "commit-msg").read_text()
        )

    def test_install_idempotent_when_already_our_hook(self) -> None:
        first = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(first.returncode, 0, msg=first.stderr)

        second = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertIn("Already installed", second.stdout)

        baks = list((self.cwd / ".git" / "hooks").glob("commit-msg.bak.*"))
        self.assertEqual(baks, [])

    def test_install_fails_outside_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as non_git:
            result = _run(["hook", "install"], cwd=Path(non_git))
            self.assertEqual(
                result.returncode, 2, msg=result.stdout + result.stderr
            )
            self.assertIn("not in a git repository", result.stderr)

    def test_uninstall_removes_our_hook(self) -> None:
        install = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(install.returncode, 0, msg=install.stderr)

        result = _run(["hook", "uninstall"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertFalse(self._target().exists())

    def test_uninstall_restores_backup_with_force(self) -> None:
        existing = self._target()
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("#!/bin/sh\necho original\n")
        existing.chmod(0o755)

        install = _run(["hook", "install"], cwd=self.cwd)
        self.assertEqual(install.returncode, 0, msg=install.stderr)

        result = _run(["hook", "uninstall", "--force"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        self.assertTrue(existing.exists())
        self.assertIn("echo original", existing.read_text())


if __name__ == "__main__":
    unittest.main()
