"""Tests for the jury-facing README."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


class ReadmeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(README.exists(), f"README not found at {README}")
        self.text = README.read_text()

    def test_readme_exists(self) -> None:
        self.assertTrue(README.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_exit_codes_table(self) -> None:
        self.assertIn("Hash mismatch", self.text)
        self.assertIn("Guard violation", self.text)

    def test_has_quickstart(self) -> None:
        # Either form is acceptable: `falsify <cmd>` (post-install
        # console entry point) or `falsify.py <cmd>` (run-as-script).
        for cmd in ("init", "verdict"):
            self.assertTrue(
                f"falsify {cmd}" in self.text or f"falsify.py {cmd}" in self.text,
                f"Quickstart missing `falsify {cmd}` / `falsify.py {cmd}`",
            )

    def test_mentions_all_three_skills(self) -> None:
        for skill in ("hypothesis-author", "falsify", "claim-audit"):
            self.assertIn(skill, self.text, f"skill missing from README: {skill}")

    def test_mentions_both_subagents(self) -> None:
        for agent in ("claim-auditor", "verdict-refresher"):
            self.assertIn(agent, self.text, f"subagent missing from README: {agent}")

    def test_has_demo_links(self) -> None:
        self.assertIn("DEMO.md", self.text)
        self.assertIn("DEMO_SHOT_LIST.md", self.text)

    def test_mentions_mit_license(self) -> None:
        self.assertIn("MIT", self.text)


if __name__ == "__main__":
    unittest.main()
