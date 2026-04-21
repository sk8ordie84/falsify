"""Tests for the GitHub Actions CI workflow."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "falsify.yml"


class CIWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            WORKFLOW_PATH.exists(), f"workflow not found at {WORKFLOW_PATH}"
        )
        self.text = WORKFLOW_PATH.read_text()
        self.parsed = yaml.safe_load(self.text)

    def test_workflow_file_exists(self) -> None:
        self.assertTrue(WORKFLOW_PATH.is_file())
        self.assertGreater(len(self.text), 0)

    def test_workflow_has_valid_yaml(self) -> None:
        self.assertIsInstance(self.parsed, dict)
        self.assertEqual(self.parsed.get("name"), "falsify CI")
        self.assertIn("jobs", self.parsed)

    def test_workflow_runs_unittest_and_smoke(self) -> None:
        self.assertIn("unittest", self.text)
        self.assertIn("smoke_test", self.text)

    def test_workflow_runs_juju_e2e(self) -> None:
        self.assertIn("falsify.py verdict juju", self.text)

    def test_workflow_has_skill_lint_job(self) -> None:
        jobs = self.parsed.get("jobs", {})
        self.assertIn(
            "skill-lint", jobs, f"expected skill-lint job, got: {list(jobs)}"
        )


if __name__ == "__main__":
    unittest.main()
