"""Tests for the .github community templates."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GH = REPO_ROOT / ".github"

BUG_REPORT = GH / "ISSUE_TEMPLATE" / "bug_report.md"
FEATURE_REQUEST = GH / "ISSUE_TEMPLATE" / "feature_request.md"
ISSUE_CONFIG = GH / "ISSUE_TEMPLATE" / "config.yml"
PR_TEMPLATE = GH / "PULL_REQUEST_TEMPLATE.md"
SECURITY = GH / "SECURITY.md"


class GithubTemplateTests(unittest.TestCase):
    def test_bug_report_exists(self) -> None:
        self.assertTrue(BUG_REPORT.is_file(), f"missing {BUG_REPORT}")

    def test_feature_request_exists(self) -> None:
        self.assertTrue(
            FEATURE_REQUEST.is_file(), f"missing {FEATURE_REQUEST}"
        )

    def test_issue_config_exists(self) -> None:
        self.assertTrue(ISSUE_CONFIG.is_file(), f"missing {ISSUE_CONFIG}")

    def test_pull_request_template_exists(self) -> None:
        self.assertTrue(PR_TEMPLATE.is_file(), f"missing {PR_TEMPLATE}")

    def test_security_md_exists(self) -> None:
        self.assertTrue(SECURITY.is_file(), f"missing {SECURITY}")

    def test_bug_report_has_doctor_section(self) -> None:
        self.assertIn("falsify doctor", BUG_REPORT.read_text())

    def test_feature_request_has_determinism_section(self) -> None:
        self.assertIn(
            "determinism", FEATURE_REQUEST.read_text().lower(),
        )

    def test_pr_template_has_checklist_with_seven_items(self) -> None:
        count = PR_TEMPLATE.read_text().count("[ ]")
        self.assertGreaterEqual(
            count, 7, f"expected >= 7 checkboxes, got {count}"
        )

    def test_security_lists_hash_collision(self) -> None:
        self.assertIn("SHA-256", SECURITY.read_text())

    def test_security_lists_guard_bypass(self) -> None:
        self.assertIn("guard", SECURITY.read_text())


if __name__ == "__main__":
    unittest.main()
