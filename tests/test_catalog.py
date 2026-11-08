"""Catalog builder (no renders, no vol writes, no network).

Covers unit-id expansion per lane scheme. Runs under pytest AND unittest.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "vf_catalog_mod", str(ROOT / "core" / "builders" / "catalog.py"))
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class TestCatalog(unittest.TestCase):
    def test_unit_ids(self):
        self.assertEqual(C._unit_ids({"unit_target": 22, "unit_scheme": "chNN"}),
                         [f"{i:02d}" for i in range(1, 23)])
        self.assertEqual(len(C._unit_ids({"unit_target": 78, "unit_scheme": "sNN"})), 78)
        self.assertEqual(C._unit_ids({"unit_target": 10, "unit_scheme": "nNN"})[0], "n01")
        self.assertEqual(C._unit_ids({"unit_target": 7, "unit_scheme": "pNN"})[-1], "p07")
        self.assertEqual(C._unit_ids({"unit_target": 5, "unit_scheme": "dNN"}), ["d%02d" % i for i in range(1, 6)])
        self.assertEqual(C._unit_ids({"unit_target": 5, "unit_scheme": "wNN"}), ["w%02d" % i for i in range(1, 6)])
        self.assertEqual(C._unit_ids({"unit_target": 36, "unit_scheme": "vNN"}), ["v%02d" % i for i in range(1, 37)])
        self.assertEqual(len(C._unit_ids({"unit_target": 36, "unit_scheme": "vNN"})), 36)

    def test_stem_aliases(self):
        self.assertEqual(C._stem_aliases("n01"), ["n01", "n1"])
        self.assertIn("ch06", C._stem_aliases("ch06"))


if __name__ == "__main__":
    unittest.main()
