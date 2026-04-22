"""Tests for Claude Code slash commands under .claude/commands/."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
NEW_CLAIM = COMMANDS_DIR / "new-claim.md"
AUDIT_CLAIMS = COMMANDS_DIR / "audit-claims.md"
SHIP_VERDICT = COMMANDS_DIR / "ship-verdict.md"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

ALL_COMMANDS = (NEW_CLAIM, AUDIT_CLAIMS, SHIP_VERDICT)


_EMOJI_RANGES = (
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F700, 0x1F77F),
    (0x1F780, 0x1F7FF),
    (0x1F800, 0x1F8FF),
    (0x1F900, 0x1F9FF),
    (0x1FA00, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
)


_FRONTMATTER_RE = re.compile(
    r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL
)


def _split_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise AssertionError("missing YAML frontmatter delimited by ---")
    data = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return data, body


class SlashCommandTests(unittest.TestCase):
    def test_commands_dir_exists(self) -> None:
        self.assertTrue(COMMANDS_DIR.is_dir(), f"missing {COMMANDS_DIR}")

    def test_new_claim_exists(self) -> None:
        self.assertTrue(NEW_CLAIM.is_file())

    def test_audit_claims_exists(self) -> None:
        self.assertTrue(AUDIT_CLAIMS.is_file())

    def test_ship_verdict_exists(self) -> None:
        self.assertTrue(SHIP_VERDICT.is_file())

    def test_each_has_frontmatter(self) -> None:
        for p in ALL_COMMANDS:
            data, _ = _split_frontmatter(p.read_text())
            desc = data.get("description", "")
            self.assertIsInstance(desc, str, f"{p.name}: description not a string")
            self.assertGreater(
                len(desc.strip()), 0,
                f"{p.name}: description is empty",
            )

    def test_new_claim_has_argument_hint(self) -> None:
        data, _ = _split_frontmatter(NEW_CLAIM.read_text())
        self.assertIn("argument-hint", data)
        self.assertTrue(str(data["argument-hint"]).strip())

    def test_ship_verdict_has_argument_hint(self) -> None:
        data, _ = _split_frontmatter(SHIP_VERDICT.read_text())
        self.assertIn("argument-hint", data)
        self.assertTrue(str(data["argument-hint"]).strip())

    def test_each_has_allowed_tools(self) -> None:
        for p in ALL_COMMANDS:
            data, _ = _split_frontmatter(p.read_text())
            self.assertIn("allowed-tools", data, f"{p.name}: missing allowed-tools")
            tools = data["allowed-tools"]
            # allowed-tools may be a YAML list or a comma-separated
            # string; normalize to a list of non-empty entries.
            if isinstance(tools, str):
                entries = [t.strip() for t in tools.split(",") if t.strip()]
            else:
                self.assertIsInstance(tools, list, f"{p.name}: allowed-tools not list/str")
                entries = [str(t).strip() for t in tools if str(t).strip()]
            self.assertGreater(
                len(entries), 0,
                f"{p.name}: allowed-tools is empty",
            )

    def test_each_has_steps_section(self) -> None:
        for p in ALL_COMMANDS:
            _, body = _split_frontmatter(p.read_text())
            self.assertRegex(
                body, r"(?mi)^##\s+Steps\b",
                f"{p.name}: missing '## Steps' heading",
            )

    def test_each_has_see_also_section(self) -> None:
        for p in ALL_COMMANDS:
            _, body = _split_frontmatter(p.read_text())
            self.assertRegex(
                body, r"(?mi)^##\s+See also\b",
                f"{p.name}: missing '## See also' heading",
            )

    def test_no_emoji_in_commands(self) -> None:
        for p in ALL_COMMANDS:
            text = p.read_text()
            for i, ch in enumerate(text):
                code = ord(ch)
                for lo, hi in _EMOJI_RANGES:
                    if lo <= code <= hi:
                        self.fail(
                            f"{p.name}: emoji/symbol U+{code:04X} "
                            f"({ch!r}) at offset {i}"
                        )

    def test_no_nested_code_fences(self) -> None:
        for p in ALL_COMMANDS:
            self.assertNotIn(
                "```", p.read_text(),
                f"{p.name}: contains triple-backtick fences; use "
                f"four-space indented blocks",
            )

    def test_readme_lists_commands(self) -> None:
        text = README.read_text()
        for name in ("/new-claim", "/audit-claims", "/ship-verdict"):
            self.assertIn(name, text, f"README missing {name}")

    def test_claude_md_lists_commands(self) -> None:
        text = CLAUDE_MD.read_text()
        for name in ("/new-claim", "/audit-claims", "/ship-verdict"):
            self.assertIn(name, text, f"CLAUDE.md missing {name}")


if __name__ == "__main__":
    unittest.main()
