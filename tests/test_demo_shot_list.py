"""Tests for docs/DEMO_SHOT_LIST.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHOT_LIST = REPO_ROOT / "docs" / "DEMO_SHOT_LIST.md"

ARTIFACTS = (
    ".claude/skills/hypothesis-author/SKILL.md",
    ".claude/skills/falsify/SKILL.md",
    ".claude/skills/claim-audit/SKILL.md",
    ".claude/agents/claim-auditor.md",
    ".claude/agents/verdict-refresher.md",
)


class DemoShotListTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SHOT_LIST.exists(), f"shot list missing at {SHOT_LIST}"
        )
        self.text = SHOT_LIST.read_text()

    def test_shot_list_exists(self) -> None:
        self.assertTrue(SHOT_LIST.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_seven_scenes(self) -> None:
        for i in range(7):
            self.assertIn(
                f"Scene {i} ",
                self.text,
                f"Scene {i} heading missing from shot list",
            )

    def test_total_budget_under_210s(self) -> None:
        # Scene headers end with "(…, Ns)" — capture every such N.
        durations = [int(m) for m in re.findall(r"(\d+)s\)", self.text)]
        self.assertGreater(
            len(durations), 0, "no scene durations parsed"
        )
        total = sum(durations)
        self.assertLess(
            total, 210, f"total runtime {total}s exceeds 210s hard cap"
        )

    def test_mentions_all_five_claude_artifacts(self) -> None:
        missing = [p for p in ARTIFACTS if p not in self.text]
        self.assertEqual(
            missing, [], f"shot list is missing artifact paths: {missing}"
        )

    def test_has_prerecord_checklist(self) -> None:
        self.assertIn("Pre-record checklist", self.text)


if __name__ == "__main__":
    unittest.main()
