"""Tests for the polished SUBMISSION.md — the judge-facing document."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBMISSION = REPO_ROOT / "SUBMISSION.md"


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


class SubmissionMdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SUBMISSION.exists(), f"missing {SUBMISSION}")
        self.text = SUBMISSION.read_text()

    def test_submission_exists(self) -> None:
        self.assertTrue(SUBMISSION.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_category_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Category\b")

    def test_has_problem_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+The problem\b")

    def test_has_scope_delivered(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Scope delivered\b")

    def test_has_30_second_repro_block(self) -> None:
        self.assertRegex(
            self.text, r"(?mi)^##\s+30-second reproduction\b",
        )
        # The block should include the canonical lock-run-verdict
        # sequence as a four-space-indented block.
        self.assertRegex(
            self.text, r"(?m)^ {4}falsify lock\b",
            "30-second reproduction missing `falsify lock` line",
        )
        self.assertRegex(
            self.text, r"(?m)^ {4}falsify verdict\b",
            "30-second reproduction missing `falsify verdict` line",
        )

    def test_has_money_shot_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+The money shot\b")

    def test_has_what_falsify_is_not(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+What falsify is NOT\b")

    def test_has_known_gaps(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Known gaps\b")

    def test_has_built_with_opus_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Built with Opus 4\.7\b")

    def test_mentions_concrete_numbers(self) -> None:
        # Any three-digit number indicates the placeholders were
        # actually filled in with real metrics.
        self.assertRegex(
            self.text, r"\b\d{3}\b",
            "SUBMISSION.md contains no three-digit number — scope "
            "counts may still be placeholder text",
        )

    def test_mentions_demo_script(self) -> None:
        self.assertIn("docs/DEMO_SCRIPT.md", self.text)

    def test_mentions_adversarial(self) -> None:
        self.assertIn("docs/ADVERSARIAL.md", self.text)

    def test_mentions_comparison(self) -> None:
        self.assertIn("docs/COMPARISON.md", self.text)

    def test_no_emoji(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in SUBMISSION.md"
                    )

    def test_no_nested_code_fences(self) -> None:
        self.assertNotIn(
            "```", self.text,
            "SUBMISSION.md must not contain triple-backtick fences; "
            "use four-space indented blocks.",
        )


if __name__ == "__main__":
    unittest.main()
