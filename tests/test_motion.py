"""Motion bank query helper (pure file reads, no renders, no network)."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "vf_mcp_mod", str(ROOT / "vf_mcp_server.py"))
M = importlib.util.module_from_spec(spec)
sys.modules["vf_mcp_mod"] = M
spec.loader.exec_module(M)


class TestMotion(unittest.TestCase):
    def test_query_all(self):
        doc = M._motion_query()
        self.assertIn("entries", doc)
        self.assertGreater(len(doc["entries"]), 0)

    def test_query_status(self):
        banked = M._motion_query(status="banked-described")["entries"]
        wanted = M._motion_query(status="wanted")["entries"]
        self.assertGreater(len(banked), 0)
        # the wanted queue may legitimately run dry (owner-closed at zero);
        # what must hold is that every returned wanted entry is wanted.
        self.assertTrue(all(e["status"] == "wanted" for e in wanted))

    def test_query_lane(self):
        nib = M._motion_query(lane="nibbana")["entries"]
        self.assertGreater(len(nib), 0)
        self.assertTrue(all("nibbana" in (e.get("used_in") or {}) for e in nib))

    def test_query_text(self):
        hits = M._motion_query(query="whirlpool")["entries"]
        self.assertGreater(len(hits), 0)


if __name__ == "__main__":
    unittest.main()

    def test_query_tags(self):
        calm = M._motion_query(tags=["calm"])["entries"]
        self.assertGreater(len(calm), 0)
        self.assertTrue(all("calm" in e.get("tags", []) for e in calm))
        both = M._motion_query(tags=["night", "calm"])["entries"]
        self.assertTrue(all({"night", "calm"} <= set(e.get("tags", [])) for e in both))
        self.assertLessEqual(len(both), len(calm))
        none = M._motion_query(tags=["no-such-tag"])["entries"]
        self.assertEqual(none, [])

    def test_every_entry_tagged(self):
        doc = M._motion_query()["entries"]
        untagged = [e["id"] for e in doc if not e.get("tags")]
        self.assertEqual(untagged, [])
