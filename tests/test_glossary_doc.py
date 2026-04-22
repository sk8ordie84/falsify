"""Static checks for docs/GLOSSARY.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = REPO_ROOT / "docs" / "GLOSSARY.md"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F2FF"
    "]"
)


class GlossaryDocTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = GLOSSARY.read_text()
        # Body is everything after the first heading.
        lines = cls.text.splitlines()
        first_heading_idx = next(
            (i for i, line in enumerate(lines) if line.startswith("# ")), 0
        )
        cls.body_after_h1 = "\n".join(lines[first_heading_idx + 1:])

    def test_file_exists(self) -> None:
        self.assertTrue(GLOSSARY.is_file(), f"missing {GLOSSARY}")

    def test_has_intro_paragraph(self) -> None:
        intro_lines: list[str] = []
        for line in self.body_after_h1.splitlines():
            stripped = line.strip()
            if stripped.startswith("##"):
                break
            if stripped:
                intro_lines.append(stripped)
        intro = " ".join(intro_lines).lower()
        self.assertTrue(
            "alphabetical" in intro or "a-z" in intro or "a to z" in intro,
            f"intro paragraph does not mention alphabetical ordering: {intro!r}",
        )

    def test_has_at_least_25_terms(self) -> None:
        term_headings = [
            line for line in self.text.splitlines()
            if line.startswith("## ")
        ]
        self.assertGreaterEqual(
            len(term_headings), 25,
            f"expected >=25 `## ` term entries; got {len(term_headings)}",
        )

    def test_has_pre_registration_term(self) -> None:
        self.assertRegex(
            self.text, r"(?mi)^## Pre-registration\b",
            "glossary missing `Pre-registration` term",
        )

    def test_has_spec_hash_term(self) -> None:
        self.assertIn(
            "Hash (spec hash)", self.text,
            "glossary missing `Hash (spec hash)` term",
        )

    def test_has_verdict_term(self) -> None:
        self.assertRegex(
            self.text, r"(?m)^## Verdict\b",
            "glossary missing `Verdict` term",
        )

    def test_has_stale_term(self) -> None:
        self.assertRegex(
            self.text, r"(?m)^## STALE\b",
            "glossary missing `STALE` term",
        )

    def test_no_emoji(self) -> None:
        match = EMOJI_RE.search(self.text)
        self.assertIsNone(
            match,
            f"glossary contains emoji at offset {match.start() if match else -1}",
        )

    def test_no_nested_code_fences(self) -> None:
        # ``` fences appearing inside a ``` block would confuse the
        # markdown parser; there should be an even count of fences.
        fence_count = sum(
            1 for line in self.text.splitlines() if line.strip().startswith("```")
        )
        self.assertEqual(
            fence_count % 2, 0,
            f"uneven code-fence count: {fence_count} (check for nesting)",
        )

    def test_readme_links_glossary(self) -> None:
        self.assertIn(
            "docs/GLOSSARY.md", README.read_text(),
            "README.md does not link to docs/GLOSSARY.md",
        )

    def test_claude_md_links_glossary(self) -> None:
        self.assertIn(
            "docs/GLOSSARY.md", CLAUDE_MD.read_text(),
            "CLAUDE.md does not link to docs/GLOSSARY.md",
        )

    def test_submission_links_glossary(self) -> None:
        self.assertIn(
            "docs/GLOSSARY.md", SUBMISSION.read_text(),
            "SUBMISSION.md does not link to docs/GLOSSARY.md",
        )


if __name__ == "__main__":
    unittest.main()
