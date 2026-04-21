"""Tests for `falsify score`."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


def _spec(echo: str, threshold: float, *, direction: str = "above") -> str:
    return textwrap.dedent(
        f"""\
        claim: "score test"
        falsification:
          failure_criteria:
            - metric: accuracy
              direction: {direction}
              threshold: {threshold}
          minimum_sample_size: 1
          stopping_rule: "once"
        experiment:
          command: "echo {echo}"
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


class ScoreCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_pass(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(_spec("0.8", 0.5))
        for cmd in (["lock", name], ["run", name], ["verdict", name]):
            self.assertEqual(_run(cmd, cwd=self.cwd).returncode, 0)

    def _make_fail(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(_spec("0.3", 0.5))
        # lock + run succeed; verdict exits 10 but writes verdict.json.
        self.assertEqual(_run(["lock", name], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["run", name], cwd=self.cwd).returncode, 0)
        _run(["verdict", name], cwd=self.cwd)

    def _make_stale(self, name: str) -> None:
        self._make_pass(name)
        verdict_path = self.cwd / ".falsify" / name / "verdict.json"
        vd = json.loads(verdict_path.read_text())
        vd["checked_at"] = (
            datetime.now(timezone.utc) - timedelta(days=10)
        ).isoformat()
        verdict_path.write_text(json.dumps(vd, indent=2, sort_keys=True))

    def _make_unlocked(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(_spec("0.8", 0.5))
        # No lock invoked → state UNLOCKED.

    def test_score_empty_repo(self) -> None:
        result = _run(["score", "--format", "json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["score"], 0.0)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["total"], 0)

    def test_score_all_pass(self) -> None:
        for n in ("p1", "p2", "p3"):
            self._make_pass(n)
        result = _run(["score", "--format", "json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["score"], 1.0)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["pass"], 3)

    def test_score_mixed(self) -> None:
        # 2 pass + 1 fail + 1 stale → (2.0 + 0 + 0 + 0) / 4 = 0.5.
        self._make_pass("p1")
        self._make_pass("p2")
        self._make_fail("f1")
        self._make_stale("s1")
        result = _run(["score", "--format", "json"], cwd=self.cwd)
        payload = json.loads(result.stdout)
        self.assertAlmostEqual(payload["score"], 0.5, places=4)
        self.assertEqual(payload["pass"], 2)
        self.assertEqual(payload["fail"], 1)
        self.assertEqual(payload["stale"], 1)
        # Threshold 0.8 → status warn (0.5 >= 0.4 = 0.8/2).
        self.assertEqual(payload["status"], "warn")
        self.assertEqual(result.returncode, 0)

    def test_score_unlocked_penalty(self) -> None:
        self._make_pass("p1")
        self._make_unlocked("u1")
        result = _run(["score", "--format", "json"], cwd=self.cwd)
        payload = json.loads(result.stdout)
        # (1.0 + (-1.0)) / 2 = 0.0 → clamp 0.0.
        self.assertEqual(payload["score"], 0.0)
        self.assertEqual(payload["unlocked"], 1)
        self.assertEqual(payload["status"], "fail")

    def test_score_json_shape(self) -> None:
        self._make_pass("p1")
        result = _run(["score", "--format", "json"], cwd=self.cwd)
        payload = json.loads(result.stdout)
        for key in (
            "score", "total", "pass", "fail", "inconclusive",
            "stale", "unrun", "unlocked", "threshold", "status",
        ):
            self.assertIn(key, payload, f"missing key: {key}")

    def test_score_shields_schema(self) -> None:
        self._make_pass("p1")
        result = _run(["score", "--format", "shields"], cwd=self.cwd)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual(payload["label"], "falsify")
        self.assertIn(payload["color"], ("brightgreen", "yellow", "red"))
        self.assertRegex(payload["message"], r"^\d\.\d{2}$")

    def test_score_svg_valid(self) -> None:
        self._make_pass("p1")
        result = _run(["score", "--format", "svg"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(result.stdout.startswith("<svg"))
        self.assertIn("</svg>", result.stdout)
        self.assertIn("1.00", result.stdout)
        # XML well-formedness — raises if malformed.
        ET.fromstring(result.stdout)

    def test_score_output_file(self) -> None:
        self._make_pass("p1")
        out = self.cwd / "badge.json"
        result = _run(
            ["score", "--format", "shields", "--output", str(out)],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertTrue(out.exists())
        json.loads(out.read_text())  # parses

    def test_score_strict_exits_on_warn(self) -> None:
        # Same fixture as test_score_mixed → status warn.
        self._make_pass("p1")
        self._make_pass("p2")
        self._make_fail("f1")
        self._make_stale("s1")
        warn_result = _run(["score", "--format", "json"], cwd=self.cwd)
        self.assertEqual(warn_result.returncode, 0)
        self.assertEqual(json.loads(warn_result.stdout)["status"], "warn")
        strict_result = _run(
            ["score", "--format", "json", "--strict"], cwd=self.cwd,
        )
        self.assertEqual(strict_result.returncode, 10)

    def test_score_xss_escape(self) -> None:
        # Defensive: even though no user input flows into the SVG today,
        # the output must always parse as XML.
        self._make_pass("p1")
        result = _run(["score", "--format", "svg"], cwd=self.cwd)
        ET.fromstring(result.stdout)


if __name__ == "__main__":
    unittest.main()
