"""Shorts automation helpers (pure data joins, no renders, no network)."""
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


def _blocks(n_verse_at=2, n_man=0):
    bs = [{"id": "b_opener", "section": "s", "type": "opener", "voice": "none",
           "text": "[bell]"}]
    for i in range(1, 7):
        bs.append({"id": f"b{i:02d}", "section": "s", "type": "narration",
                   "voice": "granny",
                   "text": "A thoughtful explanatory sentence about everything. " * 4})
    bs.insert(n_verse_at, {"id": "bv", "section": "s", "type": "verse",
                           "voice": "verse", "text": "Om namah"})
    for j in range(n_man):
        bs.append({"id": f"m{j:02d}", "section": "s", "type": "dialogue",
                   "voice": "man",
                   "text": f"\"A proper skeptical question number {j} about all of this?\""})
    for i in range(7, 11):
        bs.append({"id": f"c{i:02d}", "section": "s", "type": "narration",
                   "voice": "granny",
                   "text": "A thoughtful explanatory sentence about everything. " * 4})
    return bs


class TestShortsMine(unittest.TestCase):
    def test_verse_spans_found(self):
        cands = M._score_spans(_blocks())
        kinds = [c["kind"] for c in cands]
        self.assertIn("verse-centered", kinds)
        for c in cands:
            self.assertTrue(60 <= c["words"] <= 170)
            self.assertTrue(c["bids"])

    def test_exchange_runs_found(self):
        cands = M._score_spans(_blocks(n_man=4))
        self.assertIn("exchange", [c["kind"] for c in cands])

    def test_closer_present(self):
        cands = M._score_spans(_blocks())
        self.assertIn("closer", [c["kind"] for c in cands])


class TestRoadyPack(unittest.TestCase):
    def test_hamlet_packet(self):
        pack = M._roady_packet_data("shorts_granny_hamlet")
        self.assertNotIn("error", pack)
        self.assertTrue(pack["granny_lines"])
        self.assertTrue(all("maps_to" in ln for ln in pack["granny_lines"]))
        self.assertIn("voice_id", pack["voice"])

    def test_unknown_short(self):
        pack = M._roady_packet_data("shorts_nope_missing")
        self.assertIn("error", pack)


if __name__ == "__main__":
    unittest.main()
