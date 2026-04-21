"""Tests for the JUJU anonymized sample fixture."""

from __future__ import annotations

import csv
import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "examples" / "juju_sample"
DATA_CSV = SAMPLE_DIR / "data.csv"
METRIC_PY = SAMPLE_DIR / "metric.py"
SPEC_YAML = SAMPLE_DIR / "spec.yaml"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JujuSampleTests(unittest.TestCase):
    def test_data_csv_has_20_rows(self) -> None:
        with DATA_CSV.open(newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 20)

    def test_event_ids_are_8_char_hex(self) -> None:
        with DATA_CSV.open(newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            eid = row["event_id"]
            self.assertEqual(len(eid), 8, f"event_id length: {eid!r}")
            try:
                int(eid, 16)
            except ValueError:
                self.fail(f"event_id {eid!r} is not valid hex")

    def test_spec_yaml_validates_against_schema(self) -> None:
        falsify = _load_module("falsify", REPO_ROOT / "falsify.py")
        with SPEC_YAML.open() as f:
            spec = yaml.safe_load(f)
        schema = falsify._load_schema()
        errors: list[str] = []
        falsify._validate_against_schema(spec, schema, "", errors)
        self.assertEqual(errors, [], f"schema validation errors: {errors}")

    def test_metric_returns_tuple_of_float_and_int(self) -> None:
        metric = _load_module("juju_metric", METRIC_PY)
        result = metric.brier_score(str(DATA_CSV))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        brier, n = result
        self.assertIsInstance(brier, float)
        self.assertIsInstance(n, int)
        self.assertEqual(n, 20)

    def test_brier_in_reasonable_range(self) -> None:
        metric = _load_module("juju_metric", METRIC_PY)
        brier, _ = metric.brier_score(str(DATA_CSV))
        self.assertGreater(brier, 0.1)
        self.assertLess(brier, 0.4)


if __name__ == "__main__":
    unittest.main()
