"""Tests for the falsify orchestrator Claude Code skill."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "falsify" / "SKILL.md"

TRIGGER_PHRASES = (
    "testing whether",
    "let's verify",
    "does this work",
    "is it true that",
    "empirical claim",
    "I think X performs better",
    "run the experiment",
    "check the threshold",
    "verdict",
    "falsify this",
)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with '---' frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise AssertionError("SKILL.md frontmatter has no closing '---'")
    return rest[:end], rest[end + len("\n---\n"):]


class FalsifySkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"
        )
        self.text = SKILL_PATH.read_text()

    def test_skill_file_exists(self) -> None:
        self.assertTrue(SKILL_PATH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_frontmatter_has_required_fields(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertIsInstance(fm, dict)
        for key in ("name", "description", "allowed-tools", "context"):
            self.assertIn(key, fm, f"missing frontmatter field: {key!r}")

    def test_trigger_phrases_present(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        description = fm.get("description", "")
        self.assertIsInstance(description, str)
        hits = [p for p in TRIGGER_PHRASES if p in description]
        self.assertGreaterEqual(
            len(hits),
            5,
            f"description must contain at least 5 trigger phrases, found {len(hits)}: {hits}",
        )

    def test_body_has_required_sections(self) -> None:
        _, body = _split_frontmatter(self.text)
        body_lower = body.lower()
        for heading in (
            "when to activate",
            "routing logic",
            "hook installation",
            "hand-off",
            "examples",
        ):
            self.assertIn(
                heading, body_lower, f"required section missing: {heading!r}"
            )

    def test_context_is_fork(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertEqual(fm.get("context"), "fork")


if __name__ == "__main__":
    unittest.main()
