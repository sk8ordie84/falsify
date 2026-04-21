"""Tests for pyproject.toml."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
FALSIFY = REPO_ROOT / "falsify.py"


def _load_falsify_version() -> str:
    spec = importlib.util.spec_from_file_location("falsify_mod", FALSIFY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__


@unittest.skipUnless(tomllib is not None, "tomllib requires Python 3.11+")
class PyprojectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            PYPROJECT.exists(), f"pyproject.toml missing at {PYPROJECT}"
        )
        with PYPROJECT.open("rb") as f:
            self.data = tomllib.load(f)

    def test_pyproject_toml_exists(self) -> None:
        self.assertTrue(PYPROJECT.is_file())

    def test_pyproject_parses(self) -> None:
        self.assertIsInstance(self.data, dict)
        self.assertIn("project", self.data)
        self.assertIn("build-system", self.data)

    def test_has_project_name_falsify(self) -> None:
        self.assertEqual(self.data["project"]["name"], "falsify")

    def test_version_matches_falsify_version(self) -> None:
        pyproject_version = self.data["project"]["version"]
        module_version = _load_falsify_version()
        self.assertEqual(
            pyproject_version,
            module_version,
            f"pyproject version {pyproject_version!r} "
            f"doesn't match falsify.__version__ {module_version!r}",
        )

    def test_has_pyyaml_dependency(self) -> None:
        deps = self.data["project"].get("dependencies", [])
        self.assertTrue(
            any("pyyaml" in d.lower() for d in deps),
            f"pyyaml not in dependencies: {deps}",
        )

    def test_has_console_script(self) -> None:
        scripts = self.data["project"].get("scripts", {})
        self.assertIn("falsify", scripts)
        self.assertEqual(scripts["falsify"], "falsify:main")

    def test_license_is_mit(self) -> None:
        license_field = self.data["project"].get("license")
        if isinstance(license_field, dict):
            self.assertEqual(license_field.get("text"), "MIT")
        else:
            self.assertEqual(license_field, "MIT")

    def test_requires_python_311_or_newer(self) -> None:
        req = self.data["project"]["requires-python"]
        # Accept ">=3.11", ">=3.11,<4", or similar forms.
        self.assertIn("3.11", req)
        self.assertIn(">=", req)


if __name__ == "__main__":
    unittest.main()
