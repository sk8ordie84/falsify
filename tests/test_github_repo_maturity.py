"""Static checks for GitHub repo-maturity files.

Verifies that `.gitignore` masks regenerated run artifacts and
that `.github/` ships CODEOWNERS, FUNDING.yml, and dependabot.yml
in the shapes downstream tooling expects.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"
CODEOWNERS = REPO_ROOT / ".github" / "CODEOWNERS"
FUNDING = REPO_ROOT / ".github" / "FUNDING.yml"
DEPENDABOT = REPO_ROOT / ".github" / "dependabot.yml"


class GithubRepoMaturityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.gitignore = GITIGNORE.read_text()

    def test_gitignore_excludes_latest_run(self) -> None:
        self.assertIn(
            ".falsify/*/latest_run", self.gitignore,
            ".gitignore must exclude .falsify/*/latest_run",
        )

    def test_gitignore_excludes_verdict_json(self) -> None:
        self.assertIn(
            ".falsify/*/verdict.json", self.gitignore,
            ".gitignore must exclude .falsify/*/verdict.json",
        )

    def test_gitignore_excludes_runs_dir(self) -> None:
        self.assertIn(
            ".falsify/*/runs/", self.gitignore,
            ".gitignore must exclude .falsify/*/runs/",
        )

    def test_codeowners_exists(self) -> None:
        self.assertTrue(
            CODEOWNERS.is_file(),
            f"missing {CODEOWNERS}",
        )
        text = CODEOWNERS.read_text()
        self.assertIn("*", text, "CODEOWNERS must define a default-owner rule")

    def test_funding_yml_exists(self) -> None:
        self.assertTrue(
            FUNDING.is_file(),
            f"missing {FUNDING}",
        )

    def test_dependabot_yml_exists(self) -> None:
        self.assertTrue(
            DEPENDABOT.is_file(),
            f"missing {DEPENDABOT}",
        )

    def test_dependabot_valid_yaml(self) -> None:
        data = yaml.safe_load(DEPENDABOT.read_text())
        self.assertIsInstance(
            data, dict,
            "dependabot.yml must parse as a YAML mapping",
        )
        self.assertEqual(
            data.get("version"), 2,
            "dependabot.yml must declare `version: 2`",
        )
        updates = data.get("updates") or []
        self.assertGreaterEqual(
            len(updates), 1,
            "dependabot.yml must define at least one `updates` entry",
        )


if __name__ == "__main__":
    unittest.main()
