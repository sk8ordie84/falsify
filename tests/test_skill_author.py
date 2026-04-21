"""Tests for the hypothesis-author Claude Code skill."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = (
    REPO_ROOT / ".claude" / "skills" / "hypothesis-author" / "SKILL.md"
)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with a '---' frontmatter line")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise AssertionError("SKILL.md frontmatter has no closing '---'")
    return rest[:end], rest[end + len("\n---\n"):]


class HypothesisAuthorSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"
        )
        self.text = SKILL_PATH.read_text()

    def test_frontmatter_is_valid_yaml(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        parsed = yaml.safe_load(fm_raw)
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed.get("name"), "hypothesis-author")
        self.assertIsInstance(parsed.get("description"), str)
        self.assertGreater(len(parsed["description"]), 40)
        self.assertIn("allowed-tools", parsed)

    def test_required_sections_present(self) -> None:
        _, body = _split_frontmatter(self.text)
        body_lower = body.lower()
        for needle in (
            "when to activate",
            "dialogue",
            "falsifiability checklist",
            "spec generation template",
            "hand-off",
        ):
            self.assertIn(
                needle, body_lower, f"required heading missing: {needle!r}"
            )


if __name__ == "__main__":
    unittest.main()
