"""Tests for `falsify why`."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


def _spec(
    *, echo: str = "0.8", direction: str = "above", threshold: float = 0.5,
    min_n: int = 1, metric_fn: str = "metrics:accuracy",
) -> str:
    return textwrap.dedent(
        f"""\
        claim: "why test"
        falsification:
          failure_criteria:
            - metric: accuracy
              direction: {direction}
              threshold: {threshold}
          minimum_sample_size: {min_n}
          stopping_rule: "once"
        experiment:
          command: "echo {echo}"
          metric_fn: "{metric_fn}"
        """
    )


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FALSIFY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _load_falsify_module():
    spec = importlib.util.spec_from_file_location("_falsify_why_mod", FALSIFY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WhyCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_spec(self, name: str, spec_text: str = _spec()) -> Path:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(spec_text)
        return claim_dir

    def test_why_unlocked(self) -> None:
        self._write_spec("unl")
        result = _run(["why", "unl"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("UNLOCKED", result.stdout)
        self.assertIn("falsify lock", result.stdout)

    def test_why_unrun(self) -> None:
        self._write_spec("unr")
        self.assertEqual(_run(["lock", "unr"], cwd=self.cwd).returncode, 0)
        result = _run(["why", "unr"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("UNRUN", result.stdout)
        self.assertIn("falsify run", result.stdout)

    def test_why_pass(self) -> None:
        self._write_spec("ok")
        for cmd in (["lock", "ok"], ["run", "ok"], ["verdict", "ok"]):
            self.assertEqual(_run(cmd, cwd=self.cwd).returncode, 0)
        result = _run(["why", "ok"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("accuracy", result.stdout)
        self.assertIn("0.5", result.stdout)

    def test_why_fail(self) -> None:
        self._write_spec("bad", _spec(echo="0.3", threshold=0.8))
        _run(["lock", "bad"], cwd=self.cwd)
        _run(["run", "bad"], cwd=self.cwd)
        _run(["verdict", "bad"], cwd=self.cwd)  # exits 10 but writes
        result = _run(["why", "bad"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("violates", result.stdout)
        self.assertIn("silently lower the threshold", result.stdout)

    def test_why_stale(self) -> None:
        claim_dir = self._write_spec("drift")
        self.assertEqual(_run(["lock", "drift"], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["run", "drift"], cwd=self.cwd).returncode, 0)
        # Edit spec without re-locking — spec hash drifts.
        spec_path = claim_dir / "spec.yaml"
        spec_path.write_text(_spec(threshold=0.9))  # was 0.5
        result = _run(["why", "drift"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("STALE", result.stdout)
        # Both the stored and current hashes appear in the reasoning
        # (plus the locked line repeats the stored one — ≥2 distinct
        # short hashes in the full output).
        hashes = set(re.findall(r"sha256:([0-9a-f]{12})", result.stdout))
        self.assertGreaterEqual(len(hashes), 2, msg=result.stdout)

    def test_why_inconclusive(self) -> None:
        # Metric that returns (0.8, 3) but minimum_sample_size = 10.
        (self.cwd / "small_n.py").write_text(
            "def accuracy(_r): return (0.8, 3)\n"
        )
        self._write_spec(
            "inc",
            _spec(min_n=10, metric_fn="small_n:accuracy"),
        )
        _run(["lock", "inc"], cwd=self.cwd)
        _run(["run", "inc"], cwd=self.cwd)
        _run(["verdict", "inc"], cwd=self.cwd)  # exits 2 but writes
        result = _run(["why", "inc"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("INCONCLUSIVE", result.stdout)
        self.assertIn("sample size", result.stdout)
        self.assertIn("10", result.stdout)

    def test_why_unknown_claim(self) -> None:
        result = _run(["why", "nonexistent"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("UNKNOWN", result.stdout)
        self.assertIn("falsify list", result.stdout)

    def test_why_json_shape(self) -> None:
        self._write_spec("js")
        for cmd in (["lock", "js"], ["run", "js"], ["verdict", "js"]):
            _run(cmd, cwd=self.cwd)
        result = _run(["why", "js", "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        for key in (
            "claim", "state", "reasoning", "locked",
            "last_run", "next_action", "details",
        ):
            self.assertIn(key, payload, f"missing key: {key}")

    def test_why_verbose_has_full_hash(self) -> None:
        self._write_spec("vb")
        _run(["lock", "vb"], cwd=self.cwd)
        result = _run(["why", "vb", "--verbose"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # At least one 64-char hex hash in the output.
        self.assertRegex(result.stdout, r"[0-9a-f]{64}")

    def test_why_ago_formatter(self) -> None:
        falsify = _load_falsify_module()
        ago = falsify._ago
        now = datetime.now(timezone.utc)
        self.assertEqual(ago((now - timedelta(seconds=10)).isoformat()), "just now")
        self.assertEqual(ago((now - timedelta(minutes=2)).isoformat()), "2m ago")
        self.assertEqual(ago((now - timedelta(hours=3)).isoformat()), "3h ago")
        self.assertEqual(ago((now - timedelta(days=5)).isoformat()), "5d ago")

    def test_why_exit_code_always_zero(self) -> None:
        # Unknown claim → still exits 0.
        self.assertEqual(_run(["why", "ghost"], cwd=self.cwd).returncode, 0)
        # Each known state also exits 0.
        self._write_spec("zero")
        self.assertEqual(_run(["why", "zero"], cwd=self.cwd).returncode, 0)
        _run(["lock", "zero"], cwd=self.cwd)
        self.assertEqual(_run(["why", "zero"], cwd=self.cwd).returncode, 0)
        _run(["run", "zero"], cwd=self.cwd)
        _run(["verdict", "zero"], cwd=self.cwd)
        self.assertEqual(_run(["why", "zero"], cwd=self.cwd).returncode, 0)


if __name__ == "__main__":
    unittest.main()
