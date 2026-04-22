"""Static checks for scripts/release_check.py.

These tests do not execute the script — they only inspect the
source so they run fast and do not depend on repo mutability.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "release_check.py"
MAKEFILE = REPO_ROOT / "Makefile"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"

STDLIB_MODULES = {
    "__future__", "argparse", "ast", "collections", "hashlib",
    "json", "pathlib", "re", "subprocess", "sys", "tomllib",
    "tomli",
}


class ReleaseCheckTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SCRIPT.read_text()

    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file(), f"missing {SCRIPT}")

    def test_script_is_stdlib_only(self) -> None:
        tree = ast.parse(self.source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        non_stdlib = imported - STDLIB_MODULES
        self.assertFalse(
            non_stdlib,
            f"non-stdlib imports: {sorted(non_stdlib)}",
        )

    def test_makefile_has_release_check_target(self) -> None:
        self.assertRegex(
            MAKEFILE.read_text(),
            r"(?m)^release-check:",
            "Makefile missing `release-check:` target",
        )

    def test_contributing_mentions_release_check(self) -> None:
        text = CONTRIBUTING.read_text()
        self.assertIn("make release-check", text)

    def test_has_twelve_gates(self) -> None:
        count = self.source.count("GATE ")
        self.assertEqual(
            count, 12,
            f"expected 12 'GATE ' occurrences in script, got {count}",
        )

    def test_json_arg_documented(self) -> None:
        self.assertIn("--json", self.source)

    def test_exit_codes_documented(self) -> None:
        self.assertIn("Exit codes", self.source)
        self.assertRegex(self.source, r"\bexit\s*0\b|sys\.exit\(0\)")
        self.assertRegex(self.source, r"\bexit\s*1\b|sys\.exit\(1\)")


if __name__ == "__main__":
    unittest.main()
