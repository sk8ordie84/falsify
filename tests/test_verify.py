"""Tests for `falsify verify` — JSONL audit-trail integrity checker."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "verify test"
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


class VerifyCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _full_cycle(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(SIMPLE_SPEC)
        self.assertEqual(_run(["lock", name], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["run", name], cwd=self.cwd).returncode, 0)
        self.assertEqual(_run(["verdict", name], cwd=self.cwd).returncode, 0)

    def _export(self, *extra: str) -> Path:
        path = self.cwd / "audit.jsonl"
        result = _run(
            ["export", "--output", str(path), *extra], cwd=self.cwd
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return path

    def test_verify_produced_export_passes(self) -> None:
        self._full_cycle("one")
        audit = self._export()
        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("VALID", result.stdout)

    def test_verify_tampered_hash_fails(self) -> None:
        self._full_cycle("tamp")
        audit = self._export()
        # Change the verdict record's locked_hash to a bogus hex string.
        lines = audit.read_text().splitlines()
        tampered = []
        changed = False
        for line in lines:
            obj = json.loads(line)
            if obj.get("type") == "verdict" and not changed:
                obj["locked_hash"] = "deadbeef" * 8
                changed = True
            tampered.append(json.dumps(obj, sort_keys=True))
        self.assertTrue(changed, "no verdict record to tamper with")
        audit.write_text("\n".join(tampered) + "\n")

        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        self.assertIn("locked_hash", result.stdout)

    def test_verify_reordered_records_fails(self) -> None:
        self._full_cycle("reorder")
        audit = self._export()
        lines = audit.read_text().splitlines()
        self.assertGreaterEqual(len(lines), 2)
        # Swap the first two lines (lock and verdict for a single-spec
        # export); the verdict's earlier timestamp now precedes the
        # lock's — triggers either "verdict before any lock" or a
        # timestamp regression, both FAIL.
        lines[0], lines[1] = lines[1], lines[0]
        audit.write_text("\n".join(lines) + "\n")

        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)

    def test_verify_unknown_schema_version_is_strict_warn_not_lax_fail(self) -> None:
        self._full_cycle("sv")
        audit = self._export()
        lines = audit.read_text().splitlines()
        bumped = []
        for line in lines:
            obj = json.loads(line)
            obj["schema_version"] = 2
            bumped.append(json.dumps(obj, sort_keys=True))
        audit.write_text("\n".join(bumped) + "\n")

        lax = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(lax.returncode, 0, msg=lax.stdout + lax.stderr)
        self.assertIn("WARN", lax.stdout)

        strict = _run(["verify", str(audit), "--strict"], cwd=self.cwd)
        self.assertEqual(strict.returncode, 10, msg=strict.stdout + strict.stderr)

    def test_verify_bad_json_line_exits_2(self) -> None:
        self._full_cycle("bad")
        audit = self._export()
        with audit.open("a") as f:
            f.write("not-json\n")
        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("invalid JSON", result.stderr)

    def test_verify_json_mode_outputs_valid_json(self) -> None:
        self._full_cycle("js")
        audit = self._export()
        result = _run(["verify", str(audit), "--json"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("verdict", payload)
        self.assertIn("summary", payload)
        self.assertIn("specs", payload)

    def test_verify_timestamp_regression_fails(self) -> None:
        self._full_cycle("ts")
        audit = self._export()
        lines = audit.read_text().splitlines()
        mutated = []
        changed = False
        for line in lines:
            obj = json.loads(line)
            if obj.get("type") == "verdict" and not changed:
                # Force verdict's ts to be earlier than lock's.
                obj["ts"] = "2000-01-01T00:00:00+00:00"
                changed = True
            mutated.append(json.dumps(obj, sort_keys=True))
        self.assertTrue(changed)
        audit.write_text("\n".join(mutated) + "\n")

        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        self.assertIn("regression", result.stdout.lower())

    def test_verify_empty_file_passes(self) -> None:
        empty = self.cwd / "empty.jsonl"
        empty.write_text("")
        result = _run(["verify", str(empty)], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("VALID", result.stdout)

    def test_verify_missing_locked_hash_reference(self) -> None:
        # Hand-craft a JSONL: lock canonical_hash=A, verdict locked_hash=B.
        audit = self.cwd / "mismatch.jsonl"
        lock = {
            "type": "lock",
            "schema_version": 1,
            "name": "x",
            "ts": "2026-04-22T00:00:00+00:00",
            "canonical_hash": "a" * 64,
            "spec_snippet": {},
        }
        verdict = {
            "type": "verdict",
            "schema_version": 1,
            "name": "x",
            "ts": "2026-04-22T00:01:00+00:00",
            "state": "PASS",
            "metric_value": 0.9,
            "threshold": 0.5,
            "direction": "above",
            "n": None,
            "locked_hash": "b" * 64,
        }
        audit.write_text(
            json.dumps(lock, sort_keys=True) + "\n"
            + json.dumps(verdict, sort_keys=True) + "\n"
        )

        result = _run(["verify", str(audit)], cwd=self.cwd)
        self.assertEqual(result.returncode, 10, msg=result.stdout + result.stderr)
        self.assertIn("locked_hash", result.stdout)


if __name__ == "__main__":
    unittest.main()
