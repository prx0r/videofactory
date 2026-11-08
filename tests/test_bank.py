"""Bank emblem gate (pure: generated images in tmp dirs, no fixtures)."""
import importlib.util
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "vf_check_bank_mod", str(ROOT / "core" / "builders" / "check_bank.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class TestBank(unittest.TestCase):
    def test_rim_mean(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            white = Path(tmp) / "w.png"
            Image.new("RGB", (100, 100), (255, 255, 255)).save(white)
            self.assertGreater(B.rim_mean(str(white)), 225)
            black = Path(tmp) / "b.png"
            Image.new("RGB", (100, 100), (10, 10, 10)).save(black)
            self.assertLess(B.rim_mean(str(black)), 225)


if __name__ == "__main__":
    unittest.main()
