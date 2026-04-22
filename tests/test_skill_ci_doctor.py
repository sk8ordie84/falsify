"""Static checks for the `falsify-ci-doctor` Claude skill."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "falsify-ci-doctor" / "SKILL.md"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) for a `---`-delimited markdown file."""
    if not text.startswith("---\n"):
        raise ValueError("no leading frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("no closing frontmatter delimiter")
    frontmatter = yaml.safe_load(text[4:end]) or {}
    body = text[end + len("\n---\n"):]
    return frontmatter, body


class CiDoctorSkillTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SKILL_PATH.read_text()
        cls.frontmatter, cls.body = _split_frontmatter(cls.source)

    def test_skill_md_exists(self) -> None:
        self.assertTrue(
            SKILL_PATH.is_file(),
            f"missing {SKILL_PATH}",
        )

    def test_has_frontmatter(self) -> None:
        self.assertIsInstance(
            self.frontmatter, dict,
            "frontmatter did not parse as a YAML mapping",
        )
        self.assertGreater(
            len(self.frontmatter), 0,
            "frontmatter is empty",
        )

    def test_frontmatter_name_is_ci_doctor(self) -> None:
        self.assertEqual(
            self.frontmatter.get("name"), "falsify-ci-doctor",
            f"expected name=falsify-ci-doctor; got {self.frontmatter.get('name')!r}",
        )

    def test_frontmatter_has_description(self) -> None:
        desc = self.frontmatter.get("description", "")
        self.assertIsInstance(desc, str)
        self.assertGreater(
            len(desc), 40,
            "description should be a substantive sentence, not a stub",
        )

    def test_frontmatter_allowed_tools_list(self) -> None:
        tools = self.frontmatter.get("allowed-tools")
        self.assertIsNotNone(tools, "allowed-tools key missing")
        if isinstance(tools, str):
            items = [t.strip() for t in tools.split(",") if t.strip()]
        elif isinstance(tools, list):
            items = [str(t).strip() for t in tools if str(t).strip()]
        else:
            self.fail(f"unexpected allowed-tools type: {type(tools).__name__}")
        self.assertGreaterEqual(
            len(items), 3,
            f"allowed-tools should name >=3 tools; got {items!r}",
        )

    def test_frontmatter_context_fork(self) -> None:
        self.assertEqual(
            self.frontmatter.get("context"), "fork",
            "context must be 'fork' so CI triage runs in its own scratch space",
        )

    def test_body_has_when_to_use(self) -> None:
        self.assertIn(
            "## When to use", self.body,
            "SKILL.md body missing `## When to use` section",
        )

    def test_body_has_diagnostic_catalog(self) -> None:
        self.assertIn(
            "## Diagnostic catalog", self.body,
            "SKILL.md body missing `## Diagnostic catalog` section",
        )
        # The catalog should cover all 12 gates.
        for n in range(1, 13):
            self.assertIn(
                f"Gate {n}", self.body,
                f"diagnostic catalog missing entry for Gate {n}",
            )

    def test_body_has_output_template(self) -> None:
        self.assertIn(
            "## Output template", self.body,
            "SKILL.md body missing `## Output template` section",
        )

    def test_body_has_boundary_section(self) -> None:
        self.assertIn(
            "## Boundary with other skills", self.body,
            "SKILL.md body missing `## Boundary with other skills` section",
        )

    def test_readme_lists_ci_doctor(self) -> None:
        self.assertIn(
            "falsify-ci-doctor", README.read_text(),
            "README.md does not reference falsify-ci-doctor",
        )

    def test_claude_md_lists_ci_doctor(self) -> None:
        self.assertIn(
            "falsify-ci-doctor", CLAUDE_MD.read_text(),
            "CLAUDE.md does not reference falsify-ci-doctor",
        )


if __name__ == "__main__":
    unittest.main()
