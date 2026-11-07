"""MCP-layer pure helpers (no network, no renders, no vol writes).

Covers the pieces agents lean on through vf_* tools: stem aliases (ch6
legacy), zip naming, triage recommendation, skill-kind validation, publish
allowlist. Runs under pytest AND unittest (load the server by path — never
by bare module name; root must not claim `mcp_server`, sleepdraw owns it).
"""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "vf_mcp_mod", str(ROOT / "vf_mcp_server.py"))
M = importlib.util.module_from_spec(spec)
sys.modules["vf_mcp_mod"] = M
spec.loader.exec_module(M)


class TestMcpHelpers(unittest.TestCase):
    def test_stem_aliases(self):
        self.assertEqual(M._stem_aliases("ch6"), ["ch6", "ch06"])
        self.assertEqual(M._stem_aliases("ch14"), ["ch14"])
        self.assertEqual(M._stem_aliases("s24"), ["s24"])
        self.assertEqual(M._stem_aliases("b_opener"), ["b_opener"])

    def test_pack_name(self):
        self.assertEqual(M._pack_name("tantrasara", [15, 16, 17, 18, 19, 20, 21, 22]),
                         "tantrasara-15-22.zip")
        self.assertEqual(M._pack_name("shiva-sutras", [1]), "shiva-sutras-1.zip")
        self.assertEqual(M._pack_name("tantrasara", [14, 16, 22]),
                         "tantrasara-14+16+22.zip")

    def test_recommend(self):
        self.assertTrue(M._recommend_action(False, True, 0, False).startswith("blocked-owner"))
        self.assertTrue(M._recommend_action(True, False, 0, False).startswith("blocked-owner"))
        self.assertTrue(M._recommend_action(True, True, 99, False).startswith("awaiting-ears"))
        self.assertTrue(M._recommend_action(True, True, 0, True).startswith("ready-queue"))
        self.assertTrue(M._recommend_action(True, True, 0, False).startswith("ready-launch"))

    def test_skill_kind_validation(self):
        self.assertTrue(M._skill_kind_ok("white-gap"))
        self.assertTrue(M._skill_kind_ok("verse-gloss-missing"))
        for bad in ["", "AB", "../x", "a/b", "a" * 41, "has space"]:
            self.assertFalse(M._skill_kind_ok(bad), bad)

    def test_publish_allowlist(self):
        ok, _ = M._publish_targets_ok("/etc/passwd", "tantrasara/x.zip")
        self.assertFalse(ok)
        ok, _ = M._publish_targets_ok("~/vol/tantrasara/renders/finals/x.mp4",
                                      "../evil.zip")
        self.assertFalse(ok)
        ok, _ = M._publish_targets_ok("~/vol/tantrasara/renders/finals/x.mp4",
                                      "tantrasara/x")
        self.assertFalse(ok)  # extension required
        with mock.patch.object(os.path, "isfile", return_value=True):
            ok, reason = M._publish_targets_ok(
                "~/vol/shiva/renders/finals/s01_full.mp4", "shiva/s01_full.mp4")
            self.assertTrue(ok, reason)


if __name__ == "__main__":
    unittest.main()
