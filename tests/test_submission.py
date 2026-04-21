"""Tests for SUBMISSION.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBMISSION = REPO_ROOT / "SUBMISSION.md"

ARTIFACT_NAMES = (
    "hypothesis-author",
    "falsify",
    "claim-audit",
    "claim-auditor",
    "verdict-refresher",
)


class SubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SUBMISSION.exists(), f"SUBMISSION.md missing at {SUBMISSION}"
        )
        self.text = SUBMISSION.read_text()

    def test_submission_exists(self) -> None:
        self.assertTrue(SUBMISSION.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_tagline_section(self) -> None:
        self.assertIn("tagline", self.text.lower())

    def test_has_short_description(self) -> None:
        self.assertIn("Short description", self.text)

    def test_has_opus_47_usage(self) -> None:
        self.assertIn("How Opus 4.7 was used", self.text)

    def test_has_checklist(self) -> None:
        self.assertIn("Submission checklist", self.text)
        checkboxes = re.findall(r"^- \[ \] ", self.text, re.MULTILINE)
        self.assertGreaterEqual(
            len(checkboxes),
            5,
            f"expected >= 5 checkbox lines, found {len(checkboxes)}",
        )

    def test_mentions_all_artifacts(self) -> None:
        missing = [a for a in ARTIFACT_NAMES if a not in self.text]
        self.assertEqual(
            missing, [], f"submission is missing artifact names: {missing}"
        )

    def test_mentions_license_mit(self) -> None:
        self.assertIn("MIT", self.text)

    def test_has_deadline(self) -> None:
        self.assertIn("April 26", self.text)

    def test_has_git_for_ai_honesty_hook(self) -> None:
        self.assertIn(
            "git for AI honesty",
            self.text,
            "submission must lead with the 'git for AI honesty' hook",
        )


if __name__ == "__main__":
    unittest.main()
