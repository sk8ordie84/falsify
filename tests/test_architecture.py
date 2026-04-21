"""Tests for docs/ARCHITECTURE.md."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCH = REPO_ROOT / "docs" / "ARCHITECTURE.md"


class ArchitectureDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            ARCH.exists(), f"architecture doc missing at {ARCH}"
        )
        self.text = ARCH.read_text()

    def test_architecture_file_exists(self) -> None:
        self.assertTrue(ARCH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_data_flow_diagram(self) -> None:
        self.assertIn("canonicalize", self.text)
        self.assertIn("SHA-256", self.text)

    def test_has_invariants_section(self) -> None:
        self.assertIn("Core invariants", self.text)

    def test_has_module_table(self) -> None:
        self.assertIn("cmd_lock", self.text)
        self.assertIn("cmd_verdict", self.text)

    def test_has_extension_points(self) -> None:
        self.assertIn("MCP server", self.text)
        self.assertIn("Managed Agents", self.text)

    def test_has_design_principles(self) -> None:
        self.assertIn("Determinism over flexibility", self.text)

    def test_has_what_this_is_not(self) -> None:
        self.assertIn("What this is NOT", self.text)


if __name__ == "__main__":
    unittest.main()
