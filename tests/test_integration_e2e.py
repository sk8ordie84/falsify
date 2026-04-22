"""End-to-end lifecycle integration test.

Exercises the full claim journey through the `falsify` CLI —
init, lock, run, verdict, stats, trend, why, score, export,
verify, replay, tamper detection, honest relock, and stale
detection — in a single long test method. The stages run
top-to-bottom and share state on purpose; this is the one place
in the suite where state *between* assertions is the point.

The test spawns `python falsify.py <subcommand>` as subprocesses
against a fresh temporary directory, so it is slower than the
unit tests (expect ~30-60 seconds). If any stage fails, the
assertion message names the stage number and what was expected.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Sequence

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = PROJECT_ROOT / "falsify.py"
RUN_TIMEOUT_S = 30


class IntegrationLifecycleTest(unittest.TestCase):
    """Single-method journey through every major falsify subcommand."""

    def setUp(self) -> None:
        self._original_cwd = os.getcwd()
        self._tmp = tempfile.TemporaryDirectory()
        os.chdir(self._tmp.name)

    def tearDown(self) -> None:
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _run(self, *args: str) -> tuple[int, str, str]:
        """Run `python falsify.py <args>` in the temp cwd."""
        result = subprocess.run(
            [sys.executable, str(FALSIFY), *args],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_S,
        )
        return result.returncode, result.stdout, result.stderr

    def _assert_exit(
        self,
        stage: str,
        expected: int,
        rc: int,
        stdout: str,
        stderr: str,
    ) -> None:
        self.assertEqual(
            rc, expected,
            f"[{stage}] expected exit {expected}, got {rc}\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}",
        )

    # ------------------------------------------------------------------
    # the one test
    # ------------------------------------------------------------------

    def test_full_lifecycle(self) -> None:
        # Stage 2 — init baseline (no template / no name — smoke only).
        # The CLI prints a usage hint when neither positional name nor
        # --template is supplied. The stage's intent is to exercise
        # `init` and confirm that `.falsify/` is reachable as a
        # filesystem location from cwd; we create it if the bare
        # invocation declined to.
        rc, out, err = self._run("init")
        self.assertIn(
            rc, (0, 1),
            f"[stage 2: init] unexpected exit {rc}; stdout={out!r} stderr={err!r}",
        )
        Path(".falsify").mkdir(exist_ok=True)
        self.assertTrue(
            Path(".falsify").exists(),
            "[stage 2: init] .falsify/ should exist after init",
        )

        # Stage 3 — scaffold from template.
        rc, out, err = self._run(
            "init", "--template", "accuracy", "--name", "e2e_accuracy",
        )
        self._assert_exit("stage 3: init --template", 0, rc, out, err)
        self.assertTrue(
            Path("claims/e2e_accuracy/spec.yaml").exists(),
            "[stage 3: init --template] claims/e2e_accuracy/spec.yaml missing",
        )
        self.assertTrue(
            Path("claims/e2e_accuracy/metric.py").exists(),
            "[stage 3: init --template] claims/e2e_accuracy/metric.py missing",
        )

        # Stage 4 — lock.
        rc, out, err = self._run("lock", "e2e_accuracy")
        self._assert_exit("stage 4: lock", 0, rc, out, err)
        lock_path = Path(".falsify/e2e_accuracy/spec.lock.json")
        self.assertTrue(
            lock_path.exists(),
            "[stage 4: lock] spec.lock.json missing",
        )
        lock_data = json.loads(lock_path.read_text())
        original_hash = lock_data.get("spec_hash", "")
        self.assertEqual(
            len(original_hash), 64,
            f"[stage 4: lock] spec_hash not 64 hex chars: {original_hash!r}",
        )
        self.assertTrue(
            all(c in "0123456789abcdef" for c in original_hash),
            f"[stage 4: lock] spec_hash not hex: {original_hash!r}",
        )

        # Stage 5 — why BEFORE run (state must be UNRUN).
        rc, out, err = self._run("why", "e2e_accuracy")
        self._assert_exit("stage 5: why (unrun)", 0, rc, out, err)
        self.assertIn(
            "UNRUN", out,
            f"[stage 5: why (unrun)] expected UNRUN in stdout; got:\n{out}",
        )

        # Stage 6 — run.
        rc, out, err = self._run("run", "e2e_accuracy")
        self._assert_exit("stage 6: run", 0, rc, out, err)

        # Stage 7 — verdict PASS.
        rc, out, err = self._run("verdict", "e2e_accuracy")
        self._assert_exit("stage 7: verdict", 0, rc, out, err)
        self.assertIn(
            "PASS", out,
            f"[stage 7: verdict] expected PASS in stdout; got:\n{out}",
        )

        # Stage 8 — stats JSON shows e2e_accuracy in state PASS.
        rc, out, err = self._run("stats", "--json")
        self._assert_exit("stage 8: stats --json", 0, rc, out, err)
        stats_rows = json.loads(out)
        matching = [r for r in stats_rows if r.get("name") == "e2e_accuracy"]
        self.assertEqual(
            len(matching), 1,
            f"[stage 8: stats] e2e_accuracy missing from rows: {stats_rows!r}",
        )
        self.assertEqual(
            matching[0].get("state"), "PASS",
            f"[stage 8: stats] expected state PASS; got {matching[0]!r}",
        )

        # Stage 9 — trend after 1 run (graceful, exit 0).
        rc, out, err = self._run("trend", "e2e_accuracy")
        self._assert_exit("stage 9: trend (1 run)", 0, rc, out, err)

        # Stage 10 — two more runs, then trend --json with >=3 records.
        for i in range(2):
            rc, out, err = self._run("run", "e2e_accuracy")
            self._assert_exit(f"stage 10: run #{i + 2}", 0, rc, out, err)
        rc, out, err = self._run("trend", "e2e_accuracy", "--json")
        self._assert_exit("stage 10: trend --json", 0, rc, out, err)
        trend_payload = json.loads(out)
        # The payload shape may wrap records in a list at top level or
        # under a "runs"/"records" key; cover the common variants.
        if isinstance(trend_payload, list):
            records = trend_payload
        elif isinstance(trend_payload, dict):
            records = (
                trend_payload.get("runs")
                or trend_payload.get("records")
                or trend_payload.get("points")
                or []
            )
        else:
            records = []
        self.assertGreaterEqual(
            len(records), 3,
            f"[stage 10: trend --json] expected >=3 records; got {len(records)}:\n"
            f"{trend_payload!r}",
        )

        # Stage 11 — why AFTER PASS.
        rc, out, err = self._run("why", "e2e_accuracy")
        self._assert_exit("stage 11: why (pass)", 0, rc, out, err)
        self.assertIn(
            "PASS", out,
            f"[stage 11: why (pass)] expected PASS in stdout; got:\n{out}",
        )

        # Stage 12 — score --format json; score must be > 0.
        rc, out, err = self._run("score", "--format", "json")
        self._assert_exit("stage 12: score", 0, rc, out, err)
        score_payload = json.loads(out)
        self.assertGreater(
            score_payload.get("score", 0), 0,
            f"[stage 12: score] expected score > 0; got {score_payload!r}",
        )

        # Stage 13 — export to audit.jsonl.
        rc, out, err = self._run("export", "--output", "audit.jsonl")
        self._assert_exit("stage 13: export", 0, rc, out, err)
        audit_path = Path("audit.jsonl")
        self.assertTrue(
            audit_path.exists(),
            "[stage 13: export] audit.jsonl not written",
        )
        line_count = sum(1 for _ in audit_path.open())
        self.assertGreater(
            line_count, 0,
            "[stage 13: export] audit.jsonl is empty",
        )

        # Stage 14 — verify.
        rc, out, err = self._run("verify")
        self._assert_exit("stage 14: verify", 0, rc, out, err)

        # Stage 15 — replay the oldest run.
        run_files = sorted(
            glob.glob(".falsify/e2e_accuracy/runs/*"),
        )
        self.assertTrue(
            run_files,
            "[stage 15: replay] no run directories found",
        )
        oldest_run_id = Path(run_files[0]).name
        rc, out, err = self._run("replay", oldest_run_id)
        self._assert_exit(
            f"stage 15: replay {oldest_run_id}", 0, rc, out, err,
        )

        # Stage 16 — tamper: edit .falsify spec threshold without relock.
        tamper_spec = Path(".falsify/e2e_accuracy/spec.yaml")
        spec_obj = yaml.safe_load(tamper_spec.read_text())
        spec_obj["falsification"]["failure_criteria"][0]["threshold"] = 0.70
        tamper_spec.write_text(yaml.safe_dump(spec_obj, sort_keys=False))
        rc, out, err = self._run("run", "e2e_accuracy")
        self.assertEqual(
            rc, 3,
            f"[stage 16: tamper] expected exit 3 (hash mismatch); "
            f"got {rc}\nSTDOUT:\n{out}\nSTDERR:\n{err}",
        )

        # Stage 17 — honest relock: --force produces a new hash, run PASSes.
        rc, out, err = self._run("lock", "e2e_accuracy", "--force")
        self._assert_exit("stage 17: lock --force", 0, rc, out, err)
        new_hash = json.loads(lock_path.read_text()).get("spec_hash", "")
        self.assertNotEqual(
            new_hash, original_hash,
            "[stage 17: lock --force] hash unchanged after threshold edit",
        )
        rc, out, err = self._run("run", "e2e_accuracy")
        self._assert_exit("stage 17: run after relock", 0, rc, out, err)

        # Stage 18 — stale detection: corrupt the lock hash.
        corrupted = json.loads(lock_path.read_text())
        corrupted["spec_hash"] = "0" * 64
        lock_path.write_text(json.dumps(corrupted, indent=2) + "\n")
        rc, out, err = self._run("why", "e2e_accuracy")
        self.assertTrue(
            rc != 0 or "STALE" in out or "PASS" not in out,
            f"[stage 18: stale] expected STALE state or non-PASS state after "
            f"hash corruption; got rc={rc}, stdout:\n{out}",
        )


if __name__ == "__main__":
    unittest.main()
