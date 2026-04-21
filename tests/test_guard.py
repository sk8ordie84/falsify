"""Tests for `falsify guard` (text, scan, wrap modes)."""

from __future__ import annotations

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


def _spec(
    *,
    claim: str,
    echo: str,
    direction: str,
    threshold: float,
    min_n: int = 1,
    metric_fn: str = "metrics:accuracy",
) -> str:
    return textwrap.dedent(
        f"""\
        claim: {claim!r}
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


class GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self._tmp.name)
        shutil.copy(EXAMPLE_METRICS, self.cwd / "metrics.py")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _finalize_claim(self, name: str, spec_text: str) -> None:
        claim_dir = self.cwd / ".falsify" / name
        claim_dir.mkdir(parents=True)
        (claim_dir / "spec.yaml").write_text(spec_text)
        lock = _run(["lock", name], cwd=self.cwd)
        self.assertEqual(lock.returncode, 0, msg=lock.stderr)
        run = _run(["run", name], cwd=self.cwd)
        self.assertEqual(run.returncode, 0, msg=run.stderr)
        # verdict may exit 0 (PASS) or 10 (FAIL) — both are valid states.
        _run(["verdict", name], cwd=self.cwd)

    def test_guard_text_mode_blocks_affirmative_vs_fail(self) -> None:
        self._finalize_claim(
            "acc",
            _spec(
                claim="Model accuracy exceeds 0.95 on benchmark.",
                echo="0.30",
                direction="above",
                threshold=0.95,
            ),
        )
        result = _run(
            [
                "guard",
                "We have proven that model accuracy exceeds 0.95 on benchmark.",
            ],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 11, msg=result.stdout + result.stderr)
        self.assertIn("BLOCKED", result.stderr)

    def test_guard_text_mode_no_match(self) -> None:
        self._finalize_claim(
            "acc",
            _spec(
                claim="Model accuracy exceeds 0.95 on benchmark.",
                echo="0.30",
                direction="above",
                threshold=0.95,
            ),
        )
        # Affirmative keyword present but no fuzzy match with the claim text.
        result = _run(
            ["guard", "Release notes: UI polish confirmed for sidebar."],
            cwd=self.cwd,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_guard_scan_mode(self) -> None:
        self._finalize_claim(
            "ok",
            _spec(
                claim="Accuracy above 0.5",
                echo="0.8",
                direction="above",
                threshold=0.5,
            ),
        )
        all_pass = _run(["guard"], cwd=self.cwd)
        self.assertEqual(all_pass.returncode, 0, msg=all_pass.stderr)

        self._finalize_claim(
            "bad",
            _spec(
                claim="Accuracy above 0.9",
                echo="0.3",
                direction="above",
                threshold=0.9,
            ),
        )
        with_fail = _run(["guard"], cwd=self.cwd)
        self.assertEqual(with_fail.returncode, 10, msg=with_fail.stderr)
        self.assertIn("bad", with_fail.stderr)
        self.assertIn("FAIL", with_fail.stderr)

    def test_guard_wrap_mode_passes_through_wrapped_exit(self) -> None:
        # Wrapped command fails → return its exit code, skip scan.
        result = _run(["guard", "--", "false"], cwd=self.cwd)
        self.assertEqual(result.returncode, 1, msg=result.stderr)

    def test_guard_normalizes_case_and_punctuation(self) -> None:
        self._finalize_claim(
            "acc",
            _spec(
                claim="Model accuracy exceeds 0.95 on benchmark.",
                echo="0.30",
                direction="above",
                threshold=0.95,
            ),
        )
        noisy = "MODEL, ACCURACY: EXCEEDS!!! 0.95 on benchmark — validated!!!"
        result = _run(["guard", noisy], cwd=self.cwd)
        self.assertEqual(result.returncode, 11, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
