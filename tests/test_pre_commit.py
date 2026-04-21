"""Tests for pre-commit integration files."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_MANIFEST = REPO_ROOT / ".pre-commit-hooks.yaml"
LOCAL_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
DOCS = REPO_ROOT / "docs" / "PRE_COMMIT.md"


class PreCommitHooksManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            HOOKS_MANIFEST.exists(), f"missing {HOOKS_MANIFEST}"
        )
        self.hooks = yaml.safe_load(HOOKS_MANIFEST.read_text())

    def test_pre_commit_hooks_yaml_exists(self) -> None:
        self.assertTrue(HOOKS_MANIFEST.is_file())

    def test_pre_commit_hooks_yaml_parses(self) -> None:
        self.assertIsInstance(self.hooks, list)
        self.assertGreater(len(self.hooks), 0)

    def _find_hook(self, hook_id: str) -> dict | None:
        for hook in self.hooks:
            if isinstance(hook, dict) and hook.get("id") == hook_id:
                return hook
        return None

    def test_hooks_yaml_has_falsify_guard(self) -> None:
        hook = self._find_hook("falsify-guard")
        self.assertIsNotNone(hook, "falsify-guard hook missing")
        self.assertIn("commit-msg", hook.get("stages", []))

    def test_hooks_yaml_has_falsify_doctor(self) -> None:
        hook = self._find_hook("falsify-doctor")
        self.assertIsNotNone(hook, "falsify-doctor hook missing")
        self.assertIn("--specs-only", hook.get("args", []))

    def test_hooks_yaml_has_falsify_stats(self) -> None:
        hook = self._find_hook("falsify-stats")
        self.assertIsNotNone(hook, "falsify-stats hook missing")


class PreCommitLocalConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(LOCAL_CONFIG.exists(), f"missing {LOCAL_CONFIG}")
        self.config = yaml.safe_load(LOCAL_CONFIG.read_text())

    def test_pre_commit_config_exists(self) -> None:
        self.assertTrue(LOCAL_CONFIG.is_file())
        self.assertIsInstance(self.config, dict)
        self.assertIn("repos", self.config)

    def test_config_has_local_hooks(self) -> None:
        repos = self.config["repos"]
        local = [r for r in repos if r.get("repo") == "local"]
        self.assertEqual(
            len(local), 1, "expected exactly one local-repo entry"
        )
        hook_ids = {h.get("id") for h in local[0].get("hooks", [])}
        self.assertIn("falsify-guard-local", hook_ids)
        self.assertIn("falsify-doctor-local", hook_ids)

    def test_config_uses_pre_commit_hooks_repo(self) -> None:
        repos = self.config["repos"]
        urls = [r.get("repo", "") for r in repos]
        self.assertTrue(
            any("pre-commit/pre-commit-hooks" in u for u in urls),
            f"expected pre-commit/pre-commit-hooks entry; got {urls}",
        )


class PreCommitDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOCS.exists(), f"missing {DOCS}")
        self.text = DOCS.read_text()

    def test_docs_pre_commit_exists(self) -> None:
        self.assertTrue(DOCS.is_file())
        self.assertGreater(len(self.text), 0)

    def test_docs_has_both_use_cases(self) -> None:
        self.assertIn("Using falsify as a hook", self.text)
        self.assertIn("Our own repo", self.text)

    def test_docs_mentions_commit_msg_stage(self) -> None:
        self.assertIn("commit-msg", self.text)


if __name__ == "__main__":
    unittest.main()
