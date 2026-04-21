"""Tests for `falsify init --template ...`."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"

# Load the template registry once for the existence test.
_spec = importlib.util.spec_from_file_location("_falsify_mod", FALSIFY)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
TEMPLATES = _module._INIT_TEMPLATES


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _claim_name_for(template: str) -> str:
    """The default claim name the CLI derives from a template flag."""
    return template.replace("-", "_")


class InitTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _scaffold_lock_run_verdict(self, template: str) -> None:
        name = _claim_name_for(template)
        scaffold = _run(["init", "--template", template], cwd=self.cwd)
        self.assertEqual(
            scaffold.returncode, 0,
            msg=scaffold.stdout + scaffold.stderr,
        )
        for cmd in (["lock", name], ["run", name], ["verdict", name]):
            r = _run(cmd, cwd=self.cwd)
            self.assertEqual(
                r.returncode, 0,
                msg=f"`{' '.join(cmd)}` failed: {r.stdout}\n{r.stderr}",
            )

    def test_init_plain_unchanged(self) -> None:
        result = _run(["init", "myclaim"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        spec = self.cwd / ".falsify" / "myclaim" / "spec.yaml"
        self.assertTrue(spec.exists())
        # Template placeholders are still in the spec (the old behavior).
        self.assertIn("<", spec.read_text())

    def test_template_accuracy_end_to_end(self) -> None:
        self._scaffold_lock_run_verdict("accuracy")

    def test_template_latency_end_to_end(self) -> None:
        self._scaffold_lock_run_verdict("latency")

    def test_template_brier_end_to_end(self) -> None:
        self._scaffold_lock_run_verdict("brier")

    def test_template_llm_judge_end_to_end(self) -> None:
        self._scaffold_lock_run_verdict("llm-judge")

    def test_template_ab_end_to_end(self) -> None:
        self._scaffold_lock_run_verdict("ab")

    def test_template_unknown_name(self) -> None:
        result = _run(
            ["init", "--template", "nonsense"], cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("unknown template", result.stderr)
        self.assertIn("available:", result.stderr)

    def test_template_existing_files_no_force(self) -> None:
        first = _run(["init", "--template", "accuracy"], cwd=self.cwd)
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        second = _run(["init", "--template", "accuracy"], cwd=self.cwd)
        self.assertEqual(
            second.returncode, 2,
            msg=second.stdout + second.stderr,
        )
        self.assertIn("files exist", second.stderr)

    def test_template_existing_files_with_force(self) -> None:
        _run(["init", "--template", "accuracy"], cwd=self.cwd)
        # Mutate metric.py.
        metric_path = self.cwd / "claims" / "accuracy" / "metric.py"
        metric_path.write_text("# overwritten by user\n")
        # Re-scaffold with --force.
        result = _run(
            ["init", "--template", "accuracy", "--force"], cwd=self.cwd,
        )
        self.assertEqual(
            result.returncode, 0, msg=result.stdout + result.stderr,
        )
        # Pristine template content should be back.
        self.assertIn("def accuracy", metric_path.read_text())

    def test_template_custom_name(self) -> None:
        result = _run(
            ["init", "--template", "accuracy", "--name", "my_classifier"],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        spec_path = self.cwd / "claims" / "my_classifier" / "spec.yaml"
        self.assertTrue(spec_path.exists())
        self.assertIn(
            "claims.my_classifier.metric:accuracy",
            spec_path.read_text(),
        )
        # Mirrored into .falsify/my_classifier/ as well.
        self.assertTrue(
            (self.cwd / ".falsify" / "my_classifier" / "spec.yaml").exists()
        )

    def test_all_templates_have_required_files(self) -> None:
        for name, files in TEMPLATES.items():
            self.assertIn("spec.yaml", files, f"{name} missing spec.yaml")
            self.assertIn("metric.py", files, f"{name} missing metric.py")
            self.assertIn("README.md", files, f"{name} missing README.md")
            has_dataset = "data.csv" in files or "data.jsonl" in files
            self.assertTrue(
                has_dataset, f"{name} missing data.csv or data.jsonl",
            )


if __name__ == "__main__":
    unittest.main()
