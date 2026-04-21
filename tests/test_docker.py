"""Tests for Dockerfile, .dockerignore, docs/DOCKER.md.

These are static content checks — no docker daemon required.
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DOCKER_MD = REPO_ROOT / "docs" / "DOCKER.md"


class DockerfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOCKERFILE.exists(), f"Dockerfile missing at {DOCKERFILE}")
        self.text = DOCKERFILE.read_text()

    def test_dockerfile_exists(self) -> None:
        self.assertTrue(DOCKERFILE.is_file())
        self.assertGreater(len(self.text), 0)

    def test_dockerfile_uses_python_slim(self) -> None:
        self.assertIn("python:3.12-slim", self.text)

    def test_dockerfile_installs_package(self) -> None:
        self.assertIn("pip install", self.text)
        self.assertIn("pyproject.toml", self.text)

    def test_dockerfile_has_labels(self) -> None:
        for label in (
            "org.opencontainers.image.title",
            "org.opencontainers.image.description",
            "org.opencontainers.image.licenses",
            "org.opencontainers.image.source",
        ):
            self.assertIn(label, self.text, f"missing OCI label: {label}")

    def test_dockerfile_runs_sanity_check(self) -> None:
        self.assertIn("falsify --version", self.text)

    def test_dockerfile_default_cmd_is_demo(self) -> None:
        # CMD line referencing demo.sh (matches both shell and exec form).
        self.assertRegex(self.text, r"(?m)^CMD\s*\[?.*demo\.sh")


class DockerignoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOCKERIGNORE.exists(), f".dockerignore missing at {DOCKERIGNORE}")
        self.text = DOCKERIGNORE.read_text()

    def test_dockerignore_exists(self) -> None:
        self.assertTrue(DOCKERIGNORE.is_file())
        self.assertGreater(len(self.text), 0)

    def test_dockerignore_excludes_git(self) -> None:
        self.assertIn(".git/", self.text)

    def test_dockerignore_excludes_pycache(self) -> None:
        self.assertIn("__pycache__", self.text)

    def test_dockerignore_does_not_exclude_examples(self) -> None:
        # Scan non-comment non-empty lines; no standalone 'examples'
        # or 'examples/' rule may appear.
        for raw in self.text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            self.assertNotIn(
                line,
                ("examples", "examples/"),
                f"refuse to ignore fixtures: {raw!r}",
            )


class DockerDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DOCKER_MD.exists(), f"docs/DOCKER.md missing at {DOCKER_MD}")
        self.text = DOCKER_MD.read_text()

    def test_docker_md_exists(self) -> None:
        self.assertTrue(DOCKER_MD.is_file())
        self.assertGreater(len(self.text), 0)

    def test_docker_md_mentions_demo_auto(self) -> None:
        self.assertIn("DEMO_AUTO", self.text)

    def test_docker_md_has_mount_example(self) -> None:
        self.assertIn("-v", self.text)
        self.assertIn("/work", self.text)


if __name__ == "__main__":
    unittest.main()
