"""Tests for docs/PITCH.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PITCH = REPO_ROOT / "docs" / "PITCH.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"


class PitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PITCH.exists(), f"PITCH.md missing at {PITCH}")
        self.text = PITCH.read_text()

    def test_pitch_md_exists(self) -> None:
        self.assertTrue(PITCH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_all_length_variants(self) -> None:
        for label in ("15-word", "30-word", "60-word", "120-word", "200-word"):
            self.assertIn(
                label, self.text, f"missing length variant: {label!r}"
            )

    def test_has_video_opener(self) -> None:
        self.assertIn("Video script opener", self.text)

    def test_has_twitter_thread(self) -> None:
        self.assertIn("1/5", self.text)
        self.assertIn("5/5", self.text)

    def test_has_anti_patterns_section(self) -> None:
        self.assertIn("Anti-patterns", self.text)

    def test_submission_200w_matches_reference(self) -> None:
        # The canonical 200-word version lives in SUBMISSION.md under
        # "Short description". PITCH.md points to it; this test
        # verifies the reference actually holds those phrases.
        self.assertTrue(SUBMISSION.exists())
        body = SUBMISSION.read_text()
        match = re.search(
            r"## Short description[^\n]*\n\n(.*?)(?=\n## |\Z)",
            body,
            flags=re.S,
        )
        self.assertIsNotNone(match, "Short description section not found")
        section = match.group(1)
        self.assertIn("git for AI honesty", section)
        self.assertIn("SHA-256", section)


if __name__ == "__main__":
    unittest.main()
