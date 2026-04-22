"""Tests for `falsify trend`."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "trend test"
    falsification:
      failure_criteria:
        - metric: m
          direction: above
          threshold: 0.80
      minimum_sample_size: 1
      stopping_rule: "once"
    experiment:
      command: "echo ready"
      metric_fn: "does:not_run"
    """
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _utc_ts(offset_sec: int = 0) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(seconds=offset_sec)
    ).strftime("%Y%m%dT%H%M%S_%fZ")


def _utc_iso(offset_sec: int = 0) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(seconds=offset_sec)
    ).isoformat()


class TrendCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make_claim(
        self,
        name: str,
        values: list[float],
        *,
        threshold: float = 0.80,
        direction: str = "above",
        spec_yaml: str | None = None,
    ) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        yaml_text = (
            spec_yaml
            if spec_yaml is not None
            else SIMPLE_SPEC
            .replace("threshold: 0.80", f"threshold: {threshold}")
            .replace("direction: above", f"direction: {direction}")
        )
        (claim_dir / "spec.yaml").write_text(yaml_text)
        (claim_dir / "spec.lock.json").write_text(
            json.dumps({
                "spec_hash": "a" * 64,
                "locked_at": _utc_iso(),
                "canonical_yaml": "",
            })
        )
        runs_dir = claim_dir / "runs"
        runs_dir.mkdir()
        # Generate chronologically-ordered run dirs using an
        # incrementing index in the timestamp so sort order is stable.
        total = len(values)
        for i, v in enumerate(values):
            # Make each dir name strictly sortable — YYYYMMDDTHHMMSS_<idx>Z.
            run_id = f"20260101T000000_{i:06d}Z"
            run_dir = runs_dir / run_id
            run_dir.mkdir()
            if direction == "above":
                verdict = "PASS" if v > threshold else "FAIL"
            elif direction == "below":
                verdict = "PASS" if v < threshold else "FAIL"
            else:
                verdict = "PASS" if abs(v - threshold) < 1e-9 else "FAIL"
            (run_dir / "verdict.json").write_text(json.dumps({
                "verdict": verdict,
                "observed_value": v,
                "sample_size": 100,
                "metric": "m",
                "direction": direction,
                "threshold": threshold,
                "checked_at": (
                    datetime.now(timezone.utc)
                    - timedelta(seconds=(total - i) * 60)
                ).isoformat(),
                "run_ref": run_id,
            }))
            (run_dir / "spec.lock.json").write_text(
                json.dumps({
                    "spec_hash": "a" * 64,
                    "locked_at": _utc_iso(),
                    "canonical_yaml": "",
                })
            )

    def _make_empty_claim(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(SIMPLE_SPEC)

    def test_trend_no_runs(self) -> None:
        self._make_empty_claim("empty")
        result = _run(["trend", "empty"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("not enough runs", result.stdout)

    def test_trend_one_run(self) -> None:
        self._make_claim("one", [0.5])
        result = _run(["trend", "one"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("not enough runs", result.stdout)

    def test_trend_two_runs_flat(self) -> None:
        self._make_claim("flat", [0.5, 0.5])
        result = _run(["trend", "flat"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("trend: flat", result.stdout)

    def test_trend_improving(self) -> None:
        # Values rising toward PASS (threshold 0.80, direction above).
        self._make_claim(
            "imp", [0.60, 0.62, 0.65, 0.70, 0.75],
            threshold=0.80, direction="above",
        )
        result = _run(["trend", "imp"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("trend: improving", result.stdout)

    def test_trend_degrading(self) -> None:
        # Values falling toward FAIL (threshold 0.80, direction above).
        self._make_claim(
            "deg", [0.90, 0.85, 0.80, 0.75, 0.70],
            threshold=0.80, direction="above",
        )
        result = _run(["trend", "deg"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("trend: degrading", result.stdout)

    def test_trend_sparkline_length(self) -> None:
        self._make_claim("sl", [0.1, 0.3, 0.5, 0.7, 0.9])
        result = _run(["trend", "sl"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = result.stdout.splitlines()
        # First blank-separated block is the header; find the
        # sparkline by skipping until we hit an empty line.
        idx = lines.index("")
        sparkline = lines[idx + 1]
        # Sparkline uses Unicode block chars — each is one codepoint.
        self.assertEqual(len(sparkline), 40)

    def test_trend_custom_width(self) -> None:
        self._make_claim("cw", [0.1, 0.2, 0.3, 0.4])
        result = _run(["trend", "cw", "--width", "10"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = result.stdout.splitlines()
        idx = lines.index("")
        sparkline = lines[idx + 1]
        self.assertEqual(len(sparkline), 10)

    def test_trend_ascii_flag(self) -> None:
        self._make_claim("asc", [0.1, 0.3, 0.5, 0.7, 0.9])
        result = _run(["trend", "asc", "--ascii"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = result.stdout.splitlines()
        idx = lines.index("")
        sparkline = lines[idx + 1]
        for ch in sparkline:
            self.assertIn(ch, "_.oO#", f"non-ascii sparkline char: {ch!r}")

    def test_trend_json_shape(self) -> None:
        self._make_claim("js", [0.4, 0.5, 0.6])
        result = _run(["trend", "js", "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("records", payload)
        self.assertIn("summary", payload)
        self.assertIsInstance(payload["records"], list)
        for r in payload["records"]:
            for k in ("timestamp", "value", "n", "verdict", "spec_hash"):
                self.assertIn(k, r)

    def test_trend_threshold_overlay_on_chart(self) -> None:
        # Values span 0.5–0.9, threshold 0.80 → inside range.
        self._make_claim(
            "on",
            [0.5, 0.7, 0.9, 0.6, 0.8],
            threshold=0.80,
            direction="above",
        )
        result = _run(["trend", "on"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("(shown)", result.stdout)

    def test_trend_threshold_overlay_off_chart(self) -> None:
        # Values 0.1–0.3, threshold 0.80 → above the chart.
        self._make_claim(
            "off",
            [0.10, 0.15, 0.20, 0.25, 0.30],
            threshold=0.80,
            direction="above",
        )
        result = _run(["trend", "off"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("off-chart, above", result.stdout)

    def test_trend_last_limit(self) -> None:
        values = [i / 30 for i in range(30)]
        self._make_claim("lim", values)
        result = _run(["trend", "lim", "--last", "10"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("10 shown (of 30)", result.stdout)

    def test_trend_last_capped(self) -> None:
        values = [0.5 for _ in range(205)]
        self._make_claim("cap", values)
        result = _run(
            ["trend", "cap", "--last", "9999"], cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("200 shown (of 205)", result.stdout)

    def test_trend_unknown_claim(self) -> None:
        result = _run(["trend", "ghost"], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
