"""Tests for ROADMAP.md."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAP = REPO_ROOT / "ROADMAP.md"


class RoadmapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(ROADMAP.exists(), f"ROADMAP.md missing at {ROADMAP}")
        self.text = ROADMAP.read_text()

    def test_roadmap_exists(self) -> None:
        self.assertTrue(ROADMAP.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_now_section(self) -> None:
        self.assertRegex(self.text, r"(?m)^## Now\b")

    def test_has_next_section(self) -> None:
        self.assertRegex(self.text, r"(?m)^## Next\b")
        self.assertIn("0.2.0", self.text)

    def test_has_soon_section(self) -> None:
        self.assertRegex(self.text, r"(?m)^## Soon\b")
        self.assertIn("0.3.0", self.text)

    def test_has_later_section(self) -> None:
        self.assertRegex(self.text, r"(?m)^## Later\b")

    def test_has_non_goals(self) -> None:
        self.assertTrue(
            "won't ship" in self.text or "non-goals" in self.text,
            "ROADMAP must declare non-goals",
        )

    def test_mentions_mcp_server(self) -> None:
        self.assertIn("MCP", self.text)

    def test_mentions_managed_agents(self) -> None:
        self.assertIn("Managed Agents", self.text)

    def test_has_discipline_note(self) -> None:
        self.assertTrue(
            "feature creep" in self.text.lower()
            or "discipline" in self.text.lower(),
            "ROADMAP must include a discipline/feature-creep note",
        )


if __name__ == "__main__":
    unittest.main()
