"""Tests for `falsify stats --html`."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "stats html test"
    falsification:
      failure_criteria:
        - metric: accuracy
          direction: above
          threshold: 0.5
      minimum_sample_size: 1
      stopping_rule: "once"
    experiment:
      command: "echo 0.8"
      metric_fn: "metrics:accuracy"
    """
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class StatsHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_pass_claim(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(SIMPLE_SPEC)
        self.assertEqual(_run(["lock", name], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["run", name], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["verdict", name], cwd=self.cwd).returncode, 0)

    def test_html_mode_outputs_valid_html(self) -> None:
        self._make_pass_claim("p1")
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        parser = HTMLParser()
        parser.feed(result.stdout)
        parser.close()

    def test_html_has_doctype(self) -> None:
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(
            result.stdout.startswith("<!DOCTYPE html>"),
            f"first line: {result.stdout[:60]!r}",
        )

    def test_html_contains_spec_names(self) -> None:
        self._make_pass_claim("foo")
        self._make_pass_claim("bar")
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(">foo<", result.stdout)
        self.assertIn(">bar<", result.stdout)

    def test_html_contains_state_classes(self) -> None:
        self._make_pass_claim("ok")
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("state-PASS", result.stdout)

    def test_html_escapes_dangerous_chars(self) -> None:
        # Hand-craft a fixture bypassing the lock CLI — the placeholder
        # guard would otherwise reject the `<` in this claim text.
        claim_dir = self.cwd / ".falsify" / "xss"
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(textwrap.dedent(
            """\
            claim: "<script>alert(1)</script>"
            falsification:
              failure_criteria:
                - metric: accuracy
                  direction: above
                  threshold: 0.5
              minimum_sample_size: 1
              stopping_rule: "once"
            experiment:
              command: "echo 0.8"
              metric_fn: "metrics:accuracy"
            """
        ))
        (claim_dir / "spec.lock.json").write_text(json.dumps({
            "spec_hash": "deadbeef" * 8,
            "locked_at": "2026-04-22T00:00:00+00:00",
            "canonical_yaml": "",
        }))
        (claim_dir / "verdict.json").write_text(json.dumps({
            "verdict": "PASS",
            "observed_value": 0.8,
            "threshold": 0.5,
            "direction": "above",
            "metric": "accuracy",
            "run_ref": "test",
            "checked_at": "2026-04-22T00:00:00+00:00",
        }))

        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("&lt;script&gt;", result.stdout)
        self.assertNotIn("<script>alert(1)</script>", result.stdout)

    def test_html_output_flag_writes_file(self) -> None:
        self._make_pass_claim("outfile")
        dashboard = self.cwd / "dashboard.html"
        result = _run(
            ["stats", "--html", "--output", str(dashboard)],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(dashboard.exists())
        content = dashboard.read_text()
        self.assertTrue(content.startswith("<!DOCTYPE html>"))
        self.assertIn("outfile", content)

    def test_html_has_no_external_urls(self) -> None:
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        html = result.stdout
        # No external stylesheets / scripts.
        self.assertNotIn("<link", html)
        self.assertNotIn("<script", html)
        # At most one external URL — the GitHub footer placeholder.
        self.assertLessEqual(html.count("http://"), 0)
        self.assertLessEqual(html.count("https://"), 1)

    def test_html_has_summary_counts(self) -> None:
        self._make_pass_claim("sum1")
        result = _run(["stats", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # Summary pills show "<STATE>: <N>" pattern.
        self.assertIn("PASS: 1", result.stdout)
        self.assertIn("FAIL: 0", result.stdout)

    def test_json_and_html_mutually_exclusive(self) -> None:
        result = _run(["stats", "--json", "--html"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("not allowed with", result.stderr)


if __name__ == "__main__":
    unittest.main()
