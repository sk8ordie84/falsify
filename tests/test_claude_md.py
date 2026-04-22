"""Tests for CLAUDE.md — project instructions for Claude Code users."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


# Emoji / symbol ranges — CLAUDE.md should stay free of them.
_EMOJI_RANGES = (
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F700, 0x1F77F),
    (0x1F780, 0x1F7FF),
    (0x1F800, 0x1F8FF),
    (0x1F900, 0x1F9FF),
    (0x1FA00, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
)


class ClaudeMdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(CLAUDE_MD.exists(), f"missing {CLAUDE_MD}")
        self.text = CLAUDE_MD.read_text()

    def test_claude_md_exists_at_root(self) -> None:
        self.assertTrue(CLAUDE_MD.is_file())
        self.assertEqual(CLAUDE_MD.parent, REPO_ROOT)
        self.assertGreater(len(self.text), 0)

    def test_has_prime_directive_section(self) -> None:
        self.assertIn("## Prime Directive", self.text)
        self.assertIn(
            "Every claim is locked BEFORE it is run.", self.text
        )
        self.assertIn(
            "Hash mismatches are never silenced.", self.text
        )
        self.assertIn(
            "Threshold edits require an explicit relock", self.text
        )

    def test_mentions_all_four_skills(self) -> None:
        for skill in (
            "hypothesis-author",
            "falsify",
            "claim-audit",
            "claim-review",
        ):
            self.assertIn(
                skill, self.text, f"skill '{skill}' missing from CLAUDE.md"
            )

    def test_mentions_both_subagents(self) -> None:
        self.assertIn("claim-auditor", self.text)
        self.assertIn("verdict-refresher", self.text)

    def test_lists_development_rules(self) -> None:
        self.assertIn("## Development rules", self.text)
        # Eight numbered items — "1." through "8." must all appear.
        for n in range(1, 9):
            self.assertIn(
                f"{n}. ", self.text,
                f"numbered rule {n}. missing from Development rules",
            )

    def test_references_architecture_doc(self) -> None:
        self.assertIn("ARCHITECTURE.md", self.text)

    def test_references_adversarial_doc(self) -> None:
        self.assertIn("ADVERSARIAL.md", self.text)

    def test_references_tutorial(self) -> None:
        self.assertIn("TUTORIAL.md", self.text)

    def test_no_emoji(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in CLAUDE.md"
                    )

    def test_readme_links_claude_md(self) -> None:
        self.assertIn("CLAUDE.md", README.read_text())

    def test_contributing_references_claude_md(self) -> None:
        self.assertIn("CLAUDE.md", CONTRIBUTING.read_text())


if __name__ == "__main__":
    unittest.main()
