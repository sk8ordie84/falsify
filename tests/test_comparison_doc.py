"""Tests for docs/COMPARISON.md — feature matrix + positioning."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPARISON = REPO_ROOT / "docs" / "COMPARISON.md"
FAQ = REPO_ROOT / "docs" / "FAQ.md"
README = REPO_ROOT / "README.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


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


def _parse_table_rows(text: str) -> list[list[str]]:
    """Return a list of table rows (each row = list of cells).

    Skips the header-separator row (cells consisting only of
    dashes/colons/spaces).
    """
    rows: list[list[str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or not s.endswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # Skip alignment/separator rows like | --- | --- |
        if all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells):
            continue
        rows.append(cells)
    return rows


class ComparisonDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(COMPARISON.exists(), f"missing {COMPARISON}")
        self.text = COMPARISON.read_text()

    def test_file_exists(self) -> None:
        self.assertTrue(COMPARISON.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_feature_matrix_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Feature matrix\b")

    def test_has_positioning_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+Positioning paragraphs\b")

    def test_has_what_falsify_is_not_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+What falsify is NOT\b")

    def test_when_to_reach_section(self) -> None:
        self.assertRegex(self.text, r"(?mi)^##\s+When to reach for falsify\b")

    def test_table_has_8_columns(self) -> None:
        # Feature + 7 tool columns (falsify, MLflow, W&B, DVC,
        # OSF, pytest, pre-commit) = 8 columns total.
        rows = _parse_table_rows(self.text)
        self.assertGreaterEqual(len(rows), 2, "no table rows parsed")
        header = rows[0]
        self.assertEqual(
            len(header), 8,
            f"expected 8 columns in header; got {len(header)}: {header}",
        )
        # Every non-header row should have the same column count.
        for i, row in enumerate(rows[1:], start=1):
            self.assertEqual(
                len(row), 8,
                f"row {i} has {len(row)} cells, expected 8: {row}",
            )

    def test_table_has_15_rows(self) -> None:
        rows = _parse_table_rows(self.text)
        # rows[0] is header; remaining are feature rows.
        feature_rows = rows[1:]
        self.assertEqual(
            len(feature_rows), 15,
            f"expected 15 feature rows; got {len(feature_rows)}",
        )

    def test_mentions_all_tools(self) -> None:
        required = ["MLflow", "DVC", "OSF", "pytest", "pre-commit"]
        for tool in required:
            self.assertIn(tool, self.text, f"missing tool: {tool}")
        # W&B may appear as abbreviation or full name.
        self.assertTrue(
            "W&B" in self.text or "Weights & Biases" in self.text,
            "COMPARISON.md must mention W&B / Weights & Biases",
        )

    def test_no_emoji(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in COMPARISON.md"
                    )

    def test_no_nested_code_fences(self) -> None:
        self.assertNotIn(
            "```", self.text,
            "COMPARISON.md must not contain triple-backtick fences.",
        )

    def test_readme_links_comparison(self) -> None:
        self.assertIn("docs/COMPARISON.md", README.read_text())

    def test_faq_links_comparison(self) -> None:
        self.assertIn("COMPARISON.md", FAQ.read_text())

    def test_submission_links_comparison(self) -> None:
        self.assertIn("COMPARISON.md", SUBMISSION.read_text())

    def test_claude_md_links_comparison(self) -> None:
        self.assertIn("COMPARISON.md", CLAUDE_MD.read_text())


if __name__ == "__main__":
    unittest.main()
