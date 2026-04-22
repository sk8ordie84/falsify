"""Tests for `falsify bench`.

Unit-tests the pure helpers via direct import (no subprocess), plus a
handful of thin subprocess smoke tests with generous timeouts to
exercise the CLI wiring end-to-end. The heavy lifting stays in the
unit layer so that `make ci` does not recursively spawn bench-of-bench
processes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALSIFY = REPO_ROOT / "falsify.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import falsify  # noqa: E402

SUBPROCESS_TIMEOUT_S = 30


class BenchStatsTests(unittest.TestCase):
    """Unit tests for the pure stats / formatter / parser helpers."""

    def test_stats_calculation(self) -> None:
        stats = falsify._bench_stats([10.0, 20.0, 30.0, 40.0, 50.0])
        self.assertEqual(stats["min_ms"], 10.0)
        self.assertEqual(stats["max_ms"], 50.0)
        self.assertEqual(stats["median_ms"], 30.0)
        self.assertEqual(stats["mean_ms"], 30.0)
        self.assertAlmostEqual(stats["p95_ms"], 48.0, places=4)
        self.assertAlmostEqual(stats["stddev_ms"], 14.1421, places=3)

    def test_stats_single_sample(self) -> None:
        stats = falsify._bench_stats([42.0])
        for key in ("min_ms", "median_ms", "p95_ms",
                    "max_ms", "mean_ms"):
            self.assertEqual(stats[key], 42.0, f"expected 42 for {key}")
        self.assertEqual(stats["stddev_ms"], 0.0)

    def test_table_formatter_alignment(self) -> None:
        results = [
            {
                "command": "--help",
                "samples_ms": [42.0, 45.0, 48.0],
                "stats": falsify._bench_stats([42.0, 45.0, 48.0]),
            },
            {
                "command": "list",
                "samples_ms": [58.1, 61.2, 64.3],
                "stats": falsify._bench_stats([58.1, 61.2, 64.3]),
            },
        ]
        out = falsify._bench_format_table(results, runs=3, warmup=1)
        lines = out.strip().splitlines()
        # Header + two data rows + banner
        self.assertGreaterEqual(len(lines), 4)
        # The banner is a single free-form line; skip it.
        body = lines[1:]
        # The first column ("command") must start at position 0 on every
        # body row, and the second column must start at the same column
        # across all body rows (alignment).
        second_col_positions = [
            len(row) - len(row.lstrip(" ").split(" ", 1)[0])
            for row in body
        ]
        # Easier / more direct check: every body line contains the
        # column delimiter ("  ") at the same position for the first
        # break after the command name.
        first_break_positions = [row.index("  ") for row in body]
        self.assertTrue(
            all(p == first_break_positions[0] for p in first_break_positions),
            f"first-column widths misaligned: {first_break_positions}",
        )

    def test_parse_commands_flag(self) -> None:
        self.assertEqual(
            falsify._bench_parse_commands("list,stats"),
            ["list", "stats"],
        )
        self.assertEqual(
            falsify._bench_parse_commands(" list , stats "),
            ["list", "stats"],
        )
        self.assertEqual(
            falsify._bench_parse_commands(None),
            list(falsify._BENCH_DEFAULT_COMMANDS),
        )


class BenchCliSmokeTests(unittest.TestCase):
    """Thin subprocess tests — keep runs small and use a timeout."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(FALSIFY), "bench", *args],
            capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT_S,
        )

    def test_bench_cli_smoke_help(self) -> None:
        r = subprocess.run(
            [sys.executable, str(FALSIFY), "bench", "--help"],
            capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_S,
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("--runs", r.stdout)
        self.assertIn("--warmup", r.stdout)

    def test_bench_cli_small_run(self) -> None:
        # NOTE: `--commands=--help` (equals form) is required because
        # argparse otherwise treats the bare `--help` token as the
        # built-in help flag and refuses it as a value for --commands.
        r = self._run("--runs", "1", "--warmup", "0", "--commands=--help")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertTrue(
            "median" in r.stdout or "--help" in r.stdout,
            f"expected a bench row; got:\n{r.stdout}",
        )

    def test_bench_invalid_command_surfaces_error(self) -> None:
        r = self._run(
            "--runs", "1", "--warmup", "0",
            "--commands=nonexistent_subcommand",
        )
        self.assertNotEqual(
            r.returncode, 0,
            "bench should surface a failing sub-invocation",
        )
        self.assertIn("nonexistent_subcommand", r.stderr)

    def test_bench_json_shape(self) -> None:
        r = self._run(
            "--runs", "1", "--warmup", "0",
            "--commands=--help", "--json",
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        for key in ("runs", "warmup", "commands", "system"):
            self.assertIn(key, payload, f"payload missing key {key!r}")
        self.assertIsInstance(payload["commands"], list)
        self.assertGreaterEqual(len(payload["commands"]), 1)

    def test_bench_runs_cap(self) -> None:
        r = self._run(
            "--runs", "9999", "--warmup", "0",
            "--commands=--help", "--json",
        )
        # Acceptable shapes: either the command rejects absurd counts
        # (exit 2) or it silently caps to <=100 samples.
        if r.returncode == 0:
            payload = json.loads(r.stdout)
            n = len(payload["commands"][0]["samples_ms"])
            self.assertLessEqual(
                n, 100,
                f"expected runs to cap at 100; got n={n}",
            )
        else:
            self.assertEqual(r.returncode, 2, msg=r.stderr)

    def test_bench_warmup_not_counted(self) -> None:
        # With --warmup 0, samples_ms should equal --runs.
        r = self._run(
            "--runs", "2", "--warmup", "0",
            "--commands=--help", "--json",
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        payload = json.loads(r.stdout)
        samples = payload["commands"][0]["samples_ms"]
        self.assertEqual(
            len(samples), 2,
            f"expected 2 samples (runs=2, warmup=0); got {samples!r}",
        )

        # With --warmup 1, samples_ms still equals --runs (warmup not counted).
        r2 = self._run(
            "--runs", "2", "--warmup", "1",
            "--commands=--help", "--json",
        )
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        payload2 = json.loads(r2.stdout)
        samples2 = payload2["commands"][0]["samples_ms"]
        self.assertEqual(
            len(samples2), 2,
            f"warmup leaked into timed samples: {samples2!r}",
        )


if __name__ == "__main__":
    unittest.main()
