"""Tests for `falsify export` — JSONL audit trail."""

from __future__ import annotations

import hashlib
import json
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


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "export test"
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


def _tree_hash(root: Path) -> str:
    """Hash every file under `root` (path + content) for change detection."""
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


class ExportCommandTests(unittest.TestCase):
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

    def test_export_empty_falsify_produces_empty_output(self) -> None:
        result = _run(["export"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "")

    def test_export_single_spec_emits_lock_run_verdict_in_order(self) -> None:
        self._full_cycle("one")
        result = _run(["export", "--include-runs"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        types = [json.loads(ln)["type"] for ln in lines]
        self.assertEqual(types, ["lock", "run", "verdict"])

    def test_export_is_valid_jsonl(self) -> None:
        self._full_cycle("one")
        result = _run(["export", "--include-runs"], cwd=self.cwd)
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            json.loads(line)  # raises if any line is not valid JSON

    def test_export_each_record_has_schema_version(self) -> None:
        self._full_cycle("one")
        result = _run(["export", "--include-runs"], cwd=self.cwd)
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            self.assertEqual(
                record.get("schema_version"),
                1,
                f"record missing schema_version: {record}",
            )

    def test_export_filter_by_name(self) -> None:
        self._full_cycle("alpha-foo")
        self._full_cycle("beta-bar")
        result = _run(["export", "--name", "foo"], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        names = {
            json.loads(ln)["name"]
            for ln in result.stdout.splitlines()
            if ln.strip()
        }
        self.assertEqual(names, {"alpha-foo"})

    def test_export_filter_by_since(self) -> None:
        self._full_cycle("early")
        # Backdate early's verdict.json to 10 days ago.
        verdict_path = self.cwd / ".falsify" / "early" / "verdict.json"
        vd = json.loads(verdict_path.read_text())
        vd["checked_at"] = (
            datetime.now(timezone.utc) - timedelta(days=10)
        ).isoformat()
        verdict_path.write_text(json.dumps(vd, indent=2, sort_keys=True))

        self._full_cycle("recent")  # now

        # --since: one day ago. Only "recent" records pass; "early"'s
        # verdict (backdated) is filtered out. Note "early"'s lock is
        # still "now", so the lock passes the filter — but the verdict
        # for early is filtered out.
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        result = _run(["export", "--since", since], cwd=self.cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        records = [
            json.loads(ln)
            for ln in result.stdout.splitlines()
            if ln.strip()
        ]
        types_by_name: dict[str, set[str]] = {}
        for r in records:
            types_by_name.setdefault(r["name"], set()).add(r["type"])

        self.assertIn("recent", types_by_name)
        self.assertIn("verdict", types_by_name["recent"])
        # `early`'s backdated verdict must NOT appear.
        if "early" in types_by_name:
            self.assertNotIn("verdict", types_by_name["early"])

    def test_export_deterministic(self) -> None:
        self._full_cycle("det")
        first = _run(["export", "--include-runs"], cwd=self.cwd)
        second = _run(["export", "--include-runs"], cwd=self.cwd)
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_export_never_writes(self) -> None:
        self._full_cycle("readonly")
        falsify_dir = self.cwd / ".falsify"
        before = _tree_hash(falsify_dir)
        _run(["export", "--include-runs"], cwd=self.cwd)
        after = _tree_hash(falsify_dir)
        self.assertEqual(
            before, after, "export must not modify .falsify/"
        )

    def test_export_output_flag_writes_file(self) -> None:
        self._full_cycle("file")
        out = self.cwd / "audit.jsonl"
        result = _run(
            ["export", "--output", str(out), "--include-runs"],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(out.exists())
        content = out.read_text()
        self.assertGreater(len(content), 0)
        for line in content.splitlines():
            if line.strip():
                json.loads(line)

    def test_export_lock_record_has_canonical_hash(self) -> None:
        self._full_cycle("one")
        result = _run(["export"], cwd=self.cwd)
        locks = [
            json.loads(ln)
            for ln in result.stdout.splitlines()
            if ln.strip() and '"type": "lock"' in ln
        ]
        self.assertEqual(len(locks), 1)
        self.assertIn("canonical_hash", locks[0])
        self.assertEqual(len(locks[0]["canonical_hash"]), 64)

    def test_export_verdict_record_has_locked_hash(self) -> None:
        self._full_cycle("one")
        result = _run(["export"], cwd=self.cwd)
        verdicts = [
            json.loads(ln)
            for ln in result.stdout.splitlines()
            if ln.strip() and '"type": "verdict"' in ln
        ]
        self.assertEqual(len(verdicts), 1)
        self.assertIn("locked_hash", verdicts[0])
        self.assertEqual(len(verdicts[0]["locked_hash"]), 64)

        # Audit chain: locked_hash on verdict must match canonical_hash
        # on the earlier lock.
        locks = [
            json.loads(ln)
            for ln in result.stdout.splitlines()
            if ln.strip() and '"type": "lock"' in ln
        ]
        self.assertEqual(
            verdicts[0]["locked_hash"],
            locks[0]["canonical_hash"],
        )


if __name__ == "__main__":
    unittest.main()
