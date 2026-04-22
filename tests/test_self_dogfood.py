"""Tests for the self-dogfooding claims under claims/self/."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAIMS_DIR = REPO_ROOT / "claims" / "self"
FALSIFY_DIR = REPO_ROOT / ".falsify"
GITIGNORE = REPO_ROOT / ".gitignore"
MAKEFILE = REPO_ROOT / "Makefile"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "falsify.yml"

CLAIM_NAMES = ("cli_startup", "test_coverage_count", "claude_surface")

EXPECTED_FUNCTIONS = {
    "cli_startup": "cli_startup_ms",
    "test_coverage_count": "count_tests",
    "claude_surface": "count_claude_artifacts",
}

FORBIDDEN_IMPORTS = {
    "numpy", "pandas", "pytest", "scipy", "mlflow", "wandb",
    "sklearn", "tensorflow", "torch", "yaml", "requests",
}


class SelfDogfoodTests(unittest.TestCase):
    def test_three_self_claims_exist(self) -> None:
        for name in CLAIM_NAMES:
            spec = CLAIMS_DIR / name / "spec.yaml"
            self.assertTrue(spec.is_file(), f"missing {spec}")

    def test_each_self_claim_has_lock(self) -> None:
        for name in CLAIM_NAMES:
            lock = FALSIFY_DIR / name / "spec.lock.json"
            self.assertTrue(lock.is_file(), f"missing {lock}")

    def test_each_self_claim_has_metric(self) -> None:
        for name in CLAIM_NAMES:
            metric_path = CLAIMS_DIR / name / "metric.py"
            self.assertTrue(metric_path.is_file(), f"missing {metric_path}")
            tree = ast.parse(metric_path.read_text())
            func_names = {
                node.name for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            }
            expected = EXPECTED_FUNCTIONS[name]
            self.assertIn(
                expected, func_names,
                f"{metric_path} missing function `{expected}`",
            )

    def test_metric_files_are_stdlib_only(self) -> None:
        for name in CLAIM_NAMES:
            metric_path = CLAIMS_DIR / name / "metric.py"
            tree = ast.parse(metric_path.read_text())
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            forbidden_present = imported & FORBIDDEN_IMPORTS
            self.assertFalse(
                forbidden_present,
                f"{metric_path} imports forbidden modules: {forbidden_present}",
            )

    def test_makefile_has_dogfood_target(self) -> None:
        text = MAKEFILE.read_text()
        self.assertRegex(
            text, r"(?m)^dogfood:",
            "Makefile missing `dogfood:` target",
        )

    def test_ci_workflow_has_dogfood_job(self) -> None:
        text = CI_WORKFLOW.read_text()
        self.assertIn("dogfood", text, "CI workflow missing dogfood reference")

    def test_gitignore_excludes_runs_but_keeps_locks(self) -> None:
        text = GITIGNORE.read_text()
        # Runs dirs ignored somewhere in the file.
        self.assertRegex(
            text, r"(?m)^\.falsify/\*/runs/\s*$",
            ".gitignore missing `.falsify/*/runs/` pattern",
        )
        # Bare `.falsify/` should NOT be ignored — otherwise locks
        # are untrackable. Allow the pattern only as a comment.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotEqual(
                stripped, ".falsify/",
                "gitignore blanket-ignores .falsify/ — locks must stay trackable",
            )
            self.assertNotEqual(
                stripped, ".falsify",
                "gitignore blanket-ignores .falsify — locks must stay trackable",
            )


if __name__ == "__main__":
    unittest.main()
