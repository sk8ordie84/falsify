"""Tests for .github/workflows/release.yml."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            WORKFLOW.exists(), f"release.yml missing at {WORKFLOW}"
        )
        self.text = WORKFLOW.read_text()
        self.parsed = yaml.safe_load(self.text)

    def test_release_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())
        self.assertGreater(len(self.text), 0)

    def test_workflow_triggers_on_tag_push(self) -> None:
        self.assertIn("tags:", self.text)
        self.assertIn("v*.*.*", self.text)

    def test_workflow_has_three_jobs(self) -> None:
        jobs = self.parsed.get("jobs", {})
        for name in ("verify", "build", "release"):
            self.assertIn(name, jobs, f"missing job: {name}")

    def test_workflow_verifies_version_match(self) -> None:
        self.assertIn("__version__", self.text)
        self.assertIn("exit 1", self.text)

    def test_workflow_builds_dist(self) -> None:
        self.assertIn("python -m build", self.text)

    def test_workflow_uses_action_gh_release(self) -> None:
        self.assertIn("softprops/action-gh-release", self.text)

    def test_workflow_has_concurrency_guard(self) -> None:
        self.assertIn("concurrency:", self.text)
        self.assertIn("release-${{ github.ref }}", self.text)

    def test_workflow_has_contents_write_permission(self) -> None:
        self.assertIn("contents: write", self.text)


if __name__ == "__main__":
    unittest.main()
