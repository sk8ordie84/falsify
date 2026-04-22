"""Tests for docs/DEMO_SCRIPT.md — 90-second demo storyboard.

Disambiguated from tests/test_demo_script.py (which covers the
executable demo.sh script); this module tests the video-script
markdown document.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SCRIPT = REPO_ROOT / "docs" / "DEMO_SCRIPT.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


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


def _voiceover_block(text: str) -> str:
    """Extract the quoted voiceover paragraph from Section 3."""
    m = re.search(
        r"## Voiceover full script.*?\n\n(.*?)\n\n## ",
        text,
        re.DOTALL,
    )
    if not m:
        return ""
    body = m.group(1)
    quoted = [
        line[2:].strip() if line.startswith("> ") else ""
        for line in body.splitlines()
        if line.startswith("> ")
    ]
    return " ".join(q for q in quoted if q)


class DemoScriptDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DEMO_SCRIPT.exists(), f"missing {DEMO_SCRIPT}")
        self.text = DEMO_SCRIPT.read_text()

    def test_file_exists(self) -> None:
        self.assertTrue(DEMO_SCRIPT.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_shot_list_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Shot list\b")

    def test_has_voiceover_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Voiceover full script\b")

    def test_has_captions_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Captions\b")

    def test_has_recording_checklist(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Checklist before record\b")

    def test_has_upload_checklist(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Checklist before upload\b")

    def test_voiceover_word_count(self) -> None:
        voiceover = _voiceover_block(self.text)
        self.assertTrue(voiceover, "voiceover quoted block not found")
        word_count = len(voiceover.split())
        self.assertGreaterEqual(
            word_count, 150,
            f"voiceover has {word_count} words (< 150)",
        )
        self.assertLessEqual(
            word_count, 250,
            f"voiceover has {word_count} words (> 250)",
        )

    def test_has_srt_timestamps(self) -> None:
        matches = re.findall(r"\b\d{2}:\d{2}:\d{2},\d{3}\b", self.text)
        self.assertGreaterEqual(
            len(matches), 5,
            f"expected >= 5 SRT timestamps, got {len(matches)}",
        )

    def test_under_200_lines_approx(self) -> None:
        lines = self.text.count("\n")
        self.assertLessEqual(
            lines, 250,
            f"DEMO_SCRIPT.md has {lines} lines (> 250); keep it tight",
        )

    def test_no_emoji(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in DEMO_SCRIPT.md"
                    )

    def test_no_nested_code_fences(self) -> None:
        self.assertNotIn(
            "```", self.text,
            "DEMO_SCRIPT.md must not contain triple-backtick fences.",
        )

    def test_submission_references_demo_script(self) -> None:
        self.assertIn("DEMO_SCRIPT.md", SUBMISSION.read_text())

    def test_changelog_mentions_demo_script(self) -> None:
        self.assertIn("DEMO_SCRIPT.md", CHANGELOG.read_text())


if __name__ == "__main__":
    unittest.main()
