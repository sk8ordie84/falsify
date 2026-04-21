"""Tests for the repo-root Makefile."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"


class MakefileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MAKEFILE.exists(), f"Makefile not found at {MAKEFILE}")
        self.text = MAKEFILE.read_text()

    def test_makefile_exists(self) -> None:
        self.assertTrue(MAKEFILE.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_test_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^test:")

    def test_has_smoke_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^smoke:")

    def test_has_ci_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^ci:")

    def test_has_demo_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^demo:")

    def test_has_help_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^help:")

    def test_has_clean_target(self) -> None:
        self.assertRegex(self.text, r"(?m)^clean:")

    def test_phony_declared(self) -> None:
        self.assertIn(".PHONY", self.text)


if __name__ == "__main__":
    unittest.main()
