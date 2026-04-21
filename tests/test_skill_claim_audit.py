"""Tests for the claim-audit Claude Code skill."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "claim-audit" / "SKILL.md"

TRIGGER_PHRASES = (
    "audit this claim",
    "check this text",
    "is this accurate",
    "does this match our verdicts",
    "review this PR description",
    "lint this commit message",
    "fact check against falsify",
)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with '---' frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise AssertionError("SKILL.md frontmatter has no closing '---'")
    return rest[:end], rest[end + len("\n---\n"):]


class ClaimAuditSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"
        )
        self.text = SKILL_PATH.read_text()

    def test_skill_file_exists(self) -> None:
        self.assertTrue(SKILL_PATH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_frontmatter_required_fields(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertIsInstance(fm, dict)
        for key in ("name", "description", "allowed-tools", "context"):
            self.assertIn(key, fm, f"missing frontmatter field: {key!r}")

    def test_context_is_fork(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertEqual(fm.get("context"), "fork")

    def test_trigger_phrases_count_min_5(self) -> None:
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

    def test_body_sections_present(self) -> None:
        _, body = _split_frontmatter(self.text)
        body_lower = body.lower()
        for heading in (
            "when to activate",
            "workflow",
            "output format",
            "hand-off",
            "examples",
        ):
            self.assertIn(
                heading, body_lower, f"required section missing: {heading!r}"
            )

    def test_mentions_claim_auditor_subagent(self) -> None:
        _, body = _split_frontmatter(self.text)
        self.assertIn(
            "claim-auditor",
            body,
            "SKILL.md body must reference the claim-auditor subagent for handoff",
        )


if __name__ == "__main__":
    unittest.main()
