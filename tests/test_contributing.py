"""Tests for CONTRIBUTING.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


class ContributingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            CONTRIBUTING.exists(), f"CONTRIBUTING.md missing at {CONTRIBUTING}"
        )
        self.text = CONTRIBUTING.read_text()

    def test_contributing_exists(self) -> None:
        self.assertTrue(CONTRIBUTING.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_ground_rules(self) -> None:
        self.assertIn("Ground rules", self.text)

    def test_has_setup(self) -> None:
        self.assertIn("make install", self.text)
        self.assertIn("make ci", self.text)

    def test_has_pr_checklist(self) -> None:
        checkboxes = re.findall(r"^- \[ \] ", self.text, re.MULTILINE)
        self.assertGreaterEqual(
            len(checkboxes),
            4,
            f"expected >= 4 checkbox lines, found {len(checkboxes)}",
        )

    def test_has_skill_recipe(self) -> None:
        self.assertIn("YAML frontmatter", self.text)
        self.assertIn("context: fork", self.text)

    def test_mentions_mit_license(self) -> None:
        self.assertIn("MIT", self.text)

    def test_mentions_exit_codes(self) -> None:
        self.assertTrue(
            "0` PASS" in self.text or "exit-code contract" in self.text,
            "expected '0 PASS' or 'exit-code contract' to appear",
        )


if __name__ == "__main__":
    unittest.main()
