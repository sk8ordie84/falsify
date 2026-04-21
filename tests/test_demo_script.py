"""Tests for demo.sh — the auto-narrated end-to-end walkthrough."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO = REPO_ROOT / "demo.sh"


class DemoScriptTests(unittest.TestCase):
    """Static checks against the real demo.sh plus one full
    end-to-end run in an isolated tmpdir copy of the repo."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls._tmp.name)

        for filename in ("falsify.py", "hypothesis.schema.yaml", "demo.sh"):
            shutil.copy(REPO_ROOT / filename, cls.work / filename)
        (cls.work / "demo.sh").chmod(0o755)
        shutil.copytree(REPO_ROOT / "examples", cls.work / "examples")
        shutil.copytree(REPO_ROOT / "hooks", cls.work / "hooks")

        env = os.environ.copy()
        env["DEMO_AUTO"] = "1"
        cls.result = subprocess.run(
            ["bash", "./demo.sh"],
            cwd=cls.work,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_demo_script_exists_and_executable(self) -> None:
        self.assertTrue(DEMO.exists())
        self.assertTrue(os.access(DEMO, os.X_OK))

    def test_demo_script_uses_bash_shebang(self) -> None:
        first = DEMO.read_text().splitlines()[0]
        self.assertTrue(first.startswith("#!"), first)
        self.assertIn("bash", first)

    def test_demo_script_has_all_five_scenes(self) -> None:
        text = DEMO.read_text()
        for i in range(1, 6):
            self.assertIn(f"Scene {i}", text, f"missing Scene {i} marker")

    def test_demo_script_has_preconditions_check(self) -> None:
        self.assertIn("command -v python3", DEMO.read_text())

    def test_demo_script_runs_to_completion(self) -> None:
        self.assertEqual(
            self.result.returncode,
            0,
            msg=f"stdout:\n{self.result.stdout}\nstderr:\n{self.result.stderr}",
        )

    def test_demo_script_restores_spec(self) -> None:
        spec_path = self.work / "examples" / "juju_sample" / "spec.yaml"
        text = spec_path.read_text()
        self.assertIn("threshold: 0.25", text)
        self.assertNotIn("threshold: 0.15", text)


if __name__ == "__main__":
    unittest.main()
