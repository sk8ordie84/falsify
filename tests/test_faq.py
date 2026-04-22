"""Tests for docs/FAQ.md — objection-handler reference."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FAQ = REPO_ROOT / "docs" / "FAQ.md"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


# Emoji / symbol ranges — FAQ.md should stay free of them.
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


class FaqTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(FAQ.exists(), f"missing {FAQ}")
        self.text = FAQ.read_text()

    def test_faq_exists(self) -> None:
        self.assertTrue(FAQ.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_15_questions(self) -> None:
        headings = re.findall(r"(?m)^## .+$", self.text)
        self.assertGreaterEqual(
            len(headings), 15,
            f"expected >= 15 '## ' question headings, found "
            f"{len(headings)}: {headings}",
        )

    def test_mentions_git_hooks(self) -> None:
        self.assertIn("git hooks", self.text.lower())

    def test_mentions_osf(self) -> None:
        self.assertIn("OSF", self.text)

    def test_mentions_mlflow(self) -> None:
        lowered = self.text.lower()
        self.assertIn("mlflow", lowered)

    def test_mentions_dvc(self) -> None:
        self.assertIn("DVC", self.text)

    def test_mentions_pytest(self) -> None:
        self.assertIn("pytest", self.text.lower())

    def test_mentions_sha256(self) -> None:
        self.assertIn("SHA-256", self.text)

    def test_mentions_roadmap(self) -> None:
        self.assertTrue(
            "ROADMAP.md" in self.text or "0.3.0" in self.text,
            "FAQ should reference ROADMAP.md or version 0.3.0",
        )

    def test_no_emoji(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in FAQ.md"
                    )

    def test_no_nested_code_fences(self) -> None:
        self.assertNotIn(
            "```", self.text,
            "FAQ.md must not contain triple-backtick fences — use "
            "four-space indented code blocks instead.",
        )

    def test_readme_links_faq(self) -> None:
        self.assertIn("(docs/FAQ.md)", README.read_text())

    def test_claude_md_links_faq(self) -> None:
        self.assertIn("FAQ.md", CLAUDE_MD.read_text())


if __name__ == "__main__":
    unittest.main()
