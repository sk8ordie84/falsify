"""Unittest test-method count across tests/test_*.py.

Stdlib only. Walks the tests/ directory and counts every
function-definition whose name starts with `test_`.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "tests"


def count_tests(_run_dir) -> tuple[int, int]:
    """Return (total_test_methods, n_files_scanned)."""
    total = 0
    files = 0
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        files += 1
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name.startswith("test_")
            ):
                total += 1
    return total, files


if __name__ == "__main__":
    n_tests, n_files = count_tests(None)
    print(f"tests={n_tests} files={n_files}")
