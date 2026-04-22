"""Tests for docs/ADVERSARIAL.md and its cross-references."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADV = REPO_ROOT / "docs" / "ADVERSARIAL.md"
README = REPO_ROOT / "README.md"
SECURITY = REPO_ROOT / ".github" / "SECURITY.md"
ARCHITECTURE = REPO_ROOT / "docs" / "ARCHITECTURE.md"
SUBMISSION = REPO_ROOT / "SUBMISSION.md"


# Emoji / symbol ranges — ADVERSARIAL.md is a serious document and
# should stay free of them. Plain arrows (U+2190-U+21FF) and dashes
# are allowed (outside these ranges).
_EMOJI_RANGES = (
    (0x1F300, 0x1F5FF),  # symbols & pictographs
    (0x1F600, 0x1F64F),  # emoticons
    (0x1F680, 0x1F6FF),  # transport & map
    (0x1F700, 0x1F77F),  # alchemical
    (0x1F780, 0x1F7FF),  # geometric shapes ext
    (0x1F800, 0x1F8FF),  # arrows ext
    (0x1F900, 0x1F9FF),  # supplemental symbols
    (0x1FA00, 0x1FAFF),  # symbols & pictographs ext-a
    (0x2600, 0x26FF),    # misc symbols
    (0x2700, 0x27BF),    # dingbats
)


def _extract_section(text: str, heading: str) -> str:
    """Return the body of a '## <heading>' section up to the next '## ' line."""
    pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1) if m else ""


class AdversarialDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(ADV.exists(), f"missing {ADV}")
        self.text = ADV.read_text()

    def test_file_exists(self) -> None:
        self.assertTrue(ADV.is_file())
        self.assertGreater(len(self.text), 0)

    def test_has_scope_section(self) -> None:
        self.assertIn("Threat model scope", self.text)

    def test_has_attacks_defended_section(self) -> None:
        self.assertIn("Attacks defended", self.text)

    def test_has_attacks_not_defended_section(self) -> None:
        self.assertIn("Attacks NOT defended", self.text)

    def test_has_invariants_section(self) -> None:
        self.assertIn("Invariants relied upon", self.text)

    def test_counts_8_defended(self) -> None:
        section = _extract_section(self.text, "Attacks defended")
        # Lettered list entries a. … h. each start with bold attack name.
        matches = re.findall(r"(?m)^[a-h]\.\s+\*\*[^*]+\*\*", section)
        self.assertEqual(
            len(matches), 8,
            f"expected 8 defended attacks; found {len(matches)}: {matches}",
        )

    def test_counts_6_undefended(self) -> None:
        section = _extract_section(self.text, "Attacks NOT defended")
        matches = re.findall(r"(?m)^[a-f]\.\s+\*\*[^*]+\*\*", section)
        self.assertEqual(
            len(matches), 6,
            f"expected 6 undefended attacks; found {len(matches)}: {matches}",
        )

    def test_readme_links_adversarial(self) -> None:
        self.assertIn("ADVERSARIAL.md", README.read_text())

    def test_security_md_references_adversarial(self) -> None:
        self.assertIn("ADVERSARIAL.md", SECURITY.read_text())

    def test_architecture_references_adversarial(self) -> None:
        self.assertIn("ADVERSARIAL.md", ARCHITECTURE.read_text())

    def test_submission_references_adversarial(self) -> None:
        self.assertIn("ADVERSARIAL.md", SUBMISSION.read_text())

    def test_no_emoji_in_adversarial(self) -> None:
        for i, ch in enumerate(self.text):
            code = ord(ch)
            for lo, hi in _EMOJI_RANGES:
                if lo <= code <= hi:
                    self.fail(
                        f"emoji/symbol U+{code:04X} ({ch!r}) at offset "
                        f"{i} in ADVERSARIAL.md"
                    )


if __name__ == "__main__":
    unittest.main()
