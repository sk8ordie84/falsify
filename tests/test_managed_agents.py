"""Tests for Managed Agents manifests and deployment guide."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "managed_agents"
VERDICT_REFRESHER = MANIFEST_DIR / "verdict-refresher.yaml"
CLAIM_AUDITOR = MANIFEST_DIR / "claim-auditor.yaml"
DOCS = REPO_ROOT / "docs" / "MANAGED_AGENTS.md"


class ManagedAgentsTests(unittest.TestCase):
    def test_verdict_refresher_manifest_exists(self) -> None:
        self.assertTrue(VERDICT_REFRESHER.is_file())

    def test_claim_auditor_manifest_exists(self) -> None:
        self.assertTrue(CLAIM_AUDITOR.is_file())

    def test_both_manifests_parse_as_yaml(self) -> None:
        for path in (VERDICT_REFRESHER, CLAIM_AUDITOR):
            data = yaml.safe_load(path.read_text())
            self.assertIsInstance(
                data, dict, f"{path} must parse as a YAML mapping"
            )
            self.assertIn("name", data)

    def test_verdict_refresher_has_cron_schedule(self) -> None:
        data = yaml.safe_load(VERDICT_REFRESHER.read_text())
        self.assertIn("schedule", data)
        self.assertIn("cron", data["schedule"])
        self.assertIsInstance(data["schedule"]["cron"], str)

    def test_claim_auditor_is_on_demand(self) -> None:
        data = yaml.safe_load(CLAIM_AUDITOR.read_text())
        self.assertEqual(data.get("trigger"), "on_demand")

    def test_both_have_system_prompt(self) -> None:
        for path in (VERDICT_REFRESHER, CLAIM_AUDITOR):
            data = yaml.safe_load(path.read_text())
            prompt = data.get("system_prompt")
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 50, f"{path} system_prompt too short")

    def test_both_reference_falsify_cli(self) -> None:
        for path in (VERDICT_REFRESHER, CLAIM_AUDITOR):
            data = yaml.safe_load(path.read_text())
            self.assertIn(
                "falsify",
                data["system_prompt"],
                f"{path} system_prompt must reference `falsify`",
            )

    def test_docs_managed_agents_exists(self) -> None:
        self.assertTrue(DOCS.is_file())
        self.assertGreater(len(DOCS.read_text()), 0)

    def test_docs_mentions_console(self) -> None:
        self.assertIn("console.anthropic.com", DOCS.read_text())

    def test_docs_has_rollback_section(self) -> None:
        self.assertIn("Rollback", DOCS.read_text())

    def test_manifests_do_not_embed_api_keys(self) -> None:
        for path in (VERDICT_REFRESHER, CLAIM_AUDITOR):
            text = path.read_text()
            self.assertNotIn(
                "sk-", text, f"{path} must not embed an API key (sk-...)"
            )
            self.assertNotIn(
                "api_key",
                text.lower(),
                f"{path} must not embed an api_key field",
            )


if __name__ == "__main__":
    unittest.main()
