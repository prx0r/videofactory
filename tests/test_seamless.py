"""Seamless etch-to-GIF pipeline: pure-function tests (no renders, no network)."""
import importlib.util
import json
import sys
import tempfile
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "vf_mcp_mod", str(ROOT / "vf_mcp_server.py"))
M = importlib.util.module_from_spec(spec)
sys.modules["vf_mcp_mod"] = M
spec.loader.exec_module(M)


def _sb(path, n=12):
    blocks = [{"id": "b_opener", "section": "opener", "type": "opener",
               "voice": "none", "text": "x"}]
    for i in range(1, n + 1):
        blocks.append({"id": f"b{i}", "section": "s",
                       "type": "narration", "voice": "granny",
                       "text": "word " * (4 + i)})
    json.dump({"blocks": blocks}, open(path, "w"))


class TestRampPlan(unittest.TestCase):
    def test_lengths(self):
        durs = [550] * 12
        seq = M._ramp_plan(durs, list(range(12)), [2.0], 12.0, 15)
        self.assertEqual(len(seq), 180)

    def test_faster_means_fewer_repeats(self):
        durs = [550] * 12
        slow = M._ramp_plan(durs, list(range(12)), [0.5], 6.0, 15)
        fast = M._ramp_plan(durs, list(range(12)), [4.0], 6.0, 15)
        import collections
        cs = collections.Counter(slow)
        cf = collections.Counter(fast)
        self.assertGreater(max(cs.values()), max(cf.values()))

    def test_ramp_shape(self):
        durs = [550] * 4
        seq = M._ramp_plan(durs, [0, 1, 2, 3], [0.5, 2.0], 8.0, 15)
        self.assertEqual(len(seq), 120)
        first, second = seq[:60], seq[60:]
        import collections
        # slow step repeats frames more within its share
        self.assertGreaterEqual(len(set(first)), 1)
        self.assertEqual(len(first), 60)
        self.assertEqual(len(second), 60)
        # slow step covers fewer distinct frames per share than fast step
        self.assertLessEqual(len(set(first)), len(set(second)))

    def test_deterministic(self):
        durs = [550] * 12
        a = M._ramp_plan(durs, list(range(12)), [0.25, 0.5, 1, 2, 4], 20.0, 15)
        b = M._ramp_plan(durs, list(range(12)), [0.25, 0.5, 1, 2, 4], 20.0, 15)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 300)

    def test_reverse_order(self):
        durs = [100, 200, 300]
        seq = M._ramp_plan(durs, [2, 1, 0], [1.0], 3.0, 15)
        self.assertEqual(seq[0], 2)


class TestPassagePlan(unittest.TestCase):
    def test_explicit_total(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "storyboard_n99.json")
            _sb(p, n=10)
            r = M._passage_plan(p, "b2", "b9", 0.5, 2.6, 60.0)
            self.assertTrue(r["ok"])
            self.assertAlmostEqual(r["est_total_s"], 60.0)
            self.assertAlmostEqual(r["etch_s"], 30.0)
            self.assertIn(r["mid_bid"], [f"b{i}" for i in range(2, 10)])

    def test_words_estimate(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "storyboard_n99.json")
            _sb(p, n=4)
            r = M._passage_plan(p, "b1", "b4", 0.5, 2.0, 0.0)
            # words per block: 5,6,7,8 = 26 words at 2wps = 13s
            self.assertTrue(r["ok"])
            self.assertAlmostEqual(r["est_total_s"], 13.0)
            self.assertEqual(r["method"], "words/wps")

    def test_bad_bids(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "storyboard_n99.json")
            _sb(p, n=4)
            self.assertFalse(M._passage_plan(p, "b9", "b2", 0.5, 2.6, 0.0)["ok"])
            self.assertFalse(M._passage_plan(p, "b2", "b1", 0.5, 2.6, 0.0)["ok"])


if __name__ == "__main__":
    unittest.main()


class TestSpeakTools(unittest.TestCase):
    def test_table_prose(self):
        import vf_mcp_mod as M
        t = "[slowly] | Sanskrit | Remember it as |\n|--------|--------|\n| **cit** | Consciousness |\n| **ānanda** | Bliss |"
        out = M._speak_table_prose(t)
        self.assertTrue(out.startswith("[slowly]"))
        self.assertIn("cit: Consciousness", out)
        self.assertNotIn("|", out)
        self.assertNotIn("**", out)

    def test_table_prose_empty(self):
        import vf_mcp_mod as M
        self.assertIsNone(M._speak_table_prose("|---|"))

    def test_hazards_shape(self):
        import vf_mcp_mod as M
        h = M._speak_hazards("/home/ubuntu/nibbana/storyboards/storyboard_n01.json")
        self.assertEqual(h["total"], 0)
        self.assertIn("hashheads_n", h)

    def test_speakcheck_tool(self):
        import asyncio
        import vf_mcp_mod as M
        d = json.loads(asyncio.run(M.vf_speakcheck(project="nibbana")))
        self.assertEqual(d["units"], 10)
        self.assertEqual(d["hazards"], 0)


class TestVisualCap(unittest.TestCase):
    def test_overcap_refused_without_render(self):
        import asyncio
        import vf_mcp_mod as M
        r = asyncio.run(M.vf_seamless_draw('lamp-flame', etch_s=200.0, play_s=200.0))
        import json
        d = json.loads(r)
        self.assertFalse(d.get('ok'))
        self.assertIn('5-minute', d.get('reason', ''))
