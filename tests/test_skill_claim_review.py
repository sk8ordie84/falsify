"""Tests for the claim-review Claude skill and docs/PR_REVIEW.md."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "claim-review" / "SKILL.md"
PR_REVIEW_MD = REPO_ROOT / "docs" / "PR_REVIEW.md"
README = REPO_ROOT / "README.md"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    assert text.startswith("---\n"), "missing opening '---' frontmatter"
    rest = text[4:]
    end = rest.find("\n---\n")
    assert end >= 0, "missing closing '---' frontmatter"
    fm = yaml.safe_load(rest[:end])
    body = rest[end + len("\n---\n"):]
    return fm, body


class ClaimReviewSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(SKILL_MD.exists(), f"missing {SKILL_MD}")
        self.text = SKILL_MD.read_text()
        self.fm, self.body = _split_frontmatter(self.text)

    def test_skill_md_exists(self) -> None:
        self.assertTrue(SKILL_MD.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_frontmatter(self) -> None:
        self.assertIsInstance(self.fm, dict)
        self.assertEqual(self.fm.get("name"), "claim-review")

    def test_frontmatter_has_description(self) -> None:
        desc = self.fm.get("description")
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 40)

    def test_frontmatter_has_allowed_tools(self) -> None:
        tools = self.fm.get("allowed-tools")
        self.assertIsInstance(
            tools, list, "allowed-tools must be a YAML list"
        )
        self.assertTrue(
            any("Bash" in t for t in tools),
            f"expected at least one Bash entry in {tools!r}",
        )

    def test_frontmatter_context_fork(self) -> None:
        self.assertEqual(self.fm.get("context"), "fork")

    def test_body_has_when_to_use_section(self) -> None:
        self.assertIn("When to use", self.body)

    def test_body_has_severity_levels(self) -> None:
        self.assertIn("Severity levels", self.body)

    def test_body_has_exit_codes(self) -> None:
        self.assertIn("Exit codes", self.body)


class PrReviewDocTests(unittest.TestCase):
    def test_pr_review_doc_exists(self) -> None:
        self.assertTrue(PR_REVIEW_MD.exists(), f"missing {PR_REVIEW_MD}")
        self.assertGreater(len(PR_REVIEW_MD.read_text()), 0)

    def test_pr_review_doc_references_skill(self) -> None:
        self.assertIn("claim-review", PR_REVIEW_MD.read_text())


class ReadmeSkillListingTests(unittest.TestCase):
    def test_readme_lists_skill(self) -> None:
        self.assertTrue(README.exists())
        self.assertIn("claim-review", README.read_text())


if __name__ == "__main__":
    unittest.main()
