"""Tests for .editorconfig."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITORCONFIG = REPO_ROOT / ".editorconfig"


class EditorConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            EDITORCONFIG.exists(), f".editorconfig missing at {EDITORCONFIG}"
        )
        self.text = EDITORCONFIG.read_text()

    def test_editorconfig_exists(self) -> None:
        self.assertTrue(EDITORCONFIG.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_root_true(self) -> None:
        self.assertIn("root = true", self.text)

    def test_has_utf8(self) -> None:
        self.assertIn("charset = utf-8", self.text)

    def test_has_final_newline(self) -> None:
        self.assertIn("insert_final_newline = true", self.text)

    def test_makefile_uses_tabs(self) -> None:
        # [Makefile] section must set indent_style = tab below it.
        match = re.search(
            r"\[Makefile\](?:.*?\n)+?\s*indent_style\s*=\s*tab",
            self.text,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(
            match,
            "[Makefile] section must set `indent_style = tab`",
        )

    def test_markdown_preserves_trailing_whitespace(self) -> None:
        match = re.search(
            r"\[\*\.md\](?:.*?\n)+?\s*trim_trailing_whitespace\s*=\s*false",
            self.text,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(
            match,
            "[*.md] section must set `trim_trailing_whitespace = false`",
        )


if __name__ == "__main__":
    unittest.main()
