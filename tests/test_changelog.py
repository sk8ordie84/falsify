"""Tests for CHANGELOG.md."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
FALSIFY = REPO_ROOT / "falsify.py"


def _load_falsify_module():
    spec = importlib.util.spec_from_file_location("falsify_mod", FALSIFY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChangelogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(CHANGELOG.exists(), f"CHANGELOG missing at {CHANGELOG}")
        self.text = CHANGELOG.read_text()

    def test_changelog_exists(self) -> None:
        self.assertTrue(CHANGELOG.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_unreleased_section(self) -> None:
        self.assertIn("[Unreleased]", self.text)

    def test_has_010_section(self) -> None:
        self.assertIn("[0.1.0]", self.text)
        self.assertIn("2026-04-21", self.text)

    def test_lists_core_subcommands(self) -> None:
        for name in ("init", "lock", "verdict", "guard", "doctor", "version"):
            self.assertIn(
                name, self.text, f"changelog missing subcommand: {name!r}"
            )

    def test_mentions_three_skills(self) -> None:
        for skill in ("hypothesis-author", "falsify", "claim-audit"):
            self.assertIn(
                skill, self.text, f"changelog missing skill: {skill!r}"
            )

    def test_mentions_two_subagents(self) -> None:
        for agent in ("claim-auditor", "verdict-refresher"):
            self.assertIn(
                agent, self.text, f"changelog missing subagent: {agent!r}"
            )

    def test_mentions_mit_license(self) -> None:
        self.assertIn("MIT", self.text)

    def test_matches_version_constant(self) -> None:
        module = _load_falsify_module()
        self.assertIn(
            module.__version__,
            self.text,
            f"__version__ {module.__version__!r} not found in CHANGELOG",
        )


if __name__ == "__main__":
    unittest.main()
