"""Tests for CODE_OF_CONDUCT.md."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COC = REPO_ROOT / "CODE_OF_CONDUCT.md"


class CodeOfConductTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(COC.exists(), f"CODE_OF_CONDUCT.md missing at {COC}")
        self.text = COC.read_text()

    def test_coc_exists(self) -> None:
        self.assertTrue(COC.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_pledge_section(self) -> None:
        self.assertIn("Our pledge", self.text)

    def test_has_standards_section(self) -> None:
        self.assertIn("Our standards", self.text)

    def test_has_enforcement_section(self) -> None:
        self.assertIn("Enforcement", self.text)

    def test_mentions_contributor_covenant(self) -> None:
        self.assertIn("Contributor Covenant", self.text)

    def test_has_scope_section(self) -> None:
        self.assertIn("Scope", self.text)


if __name__ == "__main__":
    unittest.main()
