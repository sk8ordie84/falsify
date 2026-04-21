"""Tests for docs/EXAMPLES.md."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / "docs" / "EXAMPLES.md"


class ExamplesDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(EXAMPLES.exists(), f"missing {EXAMPLES}")
        self.text = EXAMPLES.read_text()

    def test_examples_md_exists(self) -> None:
        self.assertTrue(EXAMPLES.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_five_examples(self) -> None:
        for i in range(1, 6):
            self.assertRegex(
                self.text,
                rf"(?m)^## Example {i}\b",
                f"missing '## Example {i}' heading",
            )

    def _example_sections(self) -> list[str]:
        parts = re.split(r"(?m)^## Example \d+\b", self.text)
        return parts[1:]  # skip the pre-amble before Example 1

    def test_each_example_has_spec_sketch(self) -> None:
        sections = self._example_sections()
        self.assertEqual(len(sections), 5)
        for i, body in enumerate(sections, start=1):
            for needle in ("claim:", "falsification:", "threshold:"):
                self.assertIn(
                    needle,
                    body,
                    f"Example {i} missing {needle!r} in spec sketch",
                )

    def test_each_example_has_behavior(self) -> None:
        sections = self._example_sections()
        for i, body in enumerate(sections, start=1):
            self.assertIn("PASS", body, f"Example {i} missing PASS label")
            self.assertIn("FAIL", body, f"Example {i} missing FAIL label")

    def test_mentions_metric_fn(self) -> None:
        self.assertGreaterEqual(
            self.text.count("metric_fn"),
            5,
            "expected metric_fn to appear at least 5 times (once per example)",
        )

    def test_adapting_section_present(self) -> None:
        self.assertIn("Adapting an example", self.text)


if __name__ == "__main__":
    unittest.main()
