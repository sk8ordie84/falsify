"""Tests for .gitignore."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"


class GitignoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(GITIGNORE.exists(), f".gitignore missing at {GITIGNORE}")
        self.text = GITIGNORE.read_text()

    def test_gitignore_exists(self) -> None:
        self.assertTrue(GITIGNORE.is_file())
        self.assertGreater(len(self.text), 0)

    def test_ignores_pycache(self) -> None:
        self.assertIn("__pycache__", self.text)

    def test_ignores_dsstore(self) -> None:
        self.assertIn(".DS_Store", self.text)

    def test_does_not_ignore_falsify_entirely(self) -> None:
        # Scan non-comment, non-empty lines — none should be a bare
        # `.falsify/` or `.falsify` pattern (we commit per-spec
        # artifacts like spec.yaml and spec.lock.json).
        for raw in self.text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            self.assertNotIn(
                line,
                (".falsify", ".falsify/"),
                f"found overly broad ignore: {raw!r}",
            )

    def test_ignores_runs_subdir(self) -> None:
        self.assertIn(".falsify/*/runs/", self.text)


if __name__ == "__main__":
    unittest.main()
