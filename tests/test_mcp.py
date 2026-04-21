"""Tests for the upgraded MCP server (functional)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_METRICS = REPO_ROOT / "examples" / "hello_claim" / "metrics.py"

try:
    import mcp  # noqa: F401
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


SIMPLE_SPEC = textwrap.dedent(
    """\
    claim: "mcp test"
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


def _run_falsify(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "falsify.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class _ChdirCase(unittest.TestCase):
    """Mixin that creates a tmpdir and runs each test inside it.

    The plain MCP helpers read from `.falsify/` in cwd, so we point
    cwd at a controlled fixture for the duration of each test.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        self._prev_cwd = Path.cwd()
        os.chdir(self.cwd)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        os.chdir(self._prev_cwd)
        self._tmp.cleanup()

    def _full_cycle(self, name: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(SIMPLE_SPEC)
        for cmd in (["lock", name], ["run", name], ["verdict", name]):
            r = _run_falsify(cmd, cwd=self.cwd)
            self.assertEqual(r.returncode, 0, msg=r.stderr)


class PlainHelperTests(_ChdirCase):
    def test_plain_helpers_work_without_sdk(self) -> None:
        # Import only the package-level re-exports — never .server.
        from mcp_server import list_verdicts, get_stats

        self._full_cycle("alpha")
        self._full_cycle("beta")

        rows = list_verdicts()
        self.assertEqual(len(rows), 2)
        names = {r["name"] for r in rows}
        self.assertEqual(names, {"alpha", "beta"})
        for row in rows:
            for key in ("name", "state", "metric_value", "sample_size",
                        "last_run_timestamp"):
                self.assertIn(key, row)

        stats = get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["pass"], 2)
        for key in ("fail", "inconclusive", "stale", "unrun"):
            self.assertEqual(stats[key], 0)

    def test_get_verdict_not_found(self) -> None:
        from mcp_server import get_verdict
        result = get_verdict("does-not-exist")
        self.assertEqual(result, {"error": "not found"})

    def test_check_claim_unlocked_vs_locked(self) -> None:
        from mcp_server import check_claim

        # Unlocked: write only spec.yaml, never lock.
        unlocked_dir = self.cwd / ".falsify" / "unlocked"
        unlocked_dir.mkdir(parents=True)
        (unlocked_dir / "spec.yaml").write_text(SIMPLE_SPEC)
        unlocked = check_claim("unlocked")
        self.assertFalse(unlocked["locked"])
        self.assertIsNone(unlocked["hash"])
        self.assertIsNone(unlocked["latest_run"])

        # Fully cycled: locked + run + verdict.
        self._full_cycle("locked")
        locked = check_claim("locked")
        self.assertTrue(locked["locked"])
        self.assertIsInstance(locked["hash"], str)
        self.assertEqual(len(locked["hash"]), 64)
        self.assertIsNotNone(locked["latest_run"])
        self.assertIn("run_id", locked["latest_run"])


class McpSdkAdapterTests(unittest.TestCase):
    @unittest.skipIf(
        MCP_AVAILABLE,
        "mcp SDK is locally installed; can't simulate missing-SDK exit",
    )
    def test_mcp_server_import_fails_gracefully(self) -> None:
        # Spawn `python -m mcp_server` in a subprocess; expect a
        # clean exit 2 with the install hint on stderr.
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.run(
            [sys.executable, "-m", "mcp_server"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("MCP SDK not installed", result.stderr)

    @unittest.skipUnless(MCP_AVAILABLE, "mcp SDK not installed")
    def test_full_mcp_server_roundtrip(self) -> None:
        # Build the MCP Server, confirm the four tool names are
        # registered, and that the resource URI templates are exposed.
        from mcp_server.server import (
            TOOL_NAMES,
            RESOURCE_URIS,
            _build_mcp_server,
        )

        self.assertEqual(
            set(TOOL_NAMES),
            {"list_verdicts", "get_verdict", "get_stats", "check_claim"},
        )
        for uri_template in (
            "falsify://verdicts",
            "falsify://verdicts/<claim>",
            "falsify://stats",
        ):
            self.assertIn(uri_template, RESOURCE_URIS)

        server = _build_mcp_server()
        self.assertIsNotNone(server)
        # Server has request_handlers populated by the decorators.
        self.assertGreater(len(server.request_handlers), 0)


if __name__ == "__main__":
    unittest.main()
