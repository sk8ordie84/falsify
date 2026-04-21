"""Tests for the verdict-refresher subagent."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_PATH = REPO_ROOT / ".claude" / "agents" / "verdict-refresher.md"


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("agent file must start with '---' frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise AssertionError("agent frontmatter has no closing '---'")
    return rest[:end], rest[end + len("\n---\n"):]


class VerdictRefresherAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            AGENT_PATH.exists(), f"agent file not found at {AGENT_PATH}"
        )
        self.text = AGENT_PATH.read_text()

    def test_agent_file_exists(self) -> None:
        self.assertTrue(AGENT_PATH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_frontmatter_required_fields(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertIsInstance(fm, dict)
        for key in ("name", "description", "tools", "context"):
            self.assertIn(key, fm, f"missing frontmatter field: {key!r}")

    def test_context_is_fork(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        self.assertEqual(fm.get("context"), "fork")

    def test_tools_include_bash(self) -> None:
        fm_raw, _ = _split_frontmatter(self.text)
        fm = yaml.safe_load(fm_raw)
        tools = fm.get("tools", "")
        self.assertIn("Bash", tools, f"Bash missing from tools: {tools!r}")

    def test_body_sections_present(self) -> None:
        _, body = _split_frontmatter(self.text)
        body_lower = body.lower()
        for heading in (
            "role",
            "workflow",
            "output format",
            "safety",
            "when to invoke manually",
        ):
            self.assertIn(
                heading, body_lower, f"missing section: {heading!r}"
            )

    def test_mentions_falsify_stats_json(self) -> None:
        _, body = _split_frontmatter(self.text)
        self.assertIn(
            "falsify.py stats --json",
            body,
            "body must reference `falsify.py stats --json` as the enumeration step",
        )

    def test_mentions_retry_cap(self) -> None:
        _, body = _split_frontmatter(self.text)
        lowered = body.lower()
        self.assertTrue(
            "2 times" in lowered or "twice" in lowered,
            "body must mention a retry cap of 2 times / twice",
        )


if __name__ == "__main__":
    unittest.main()
