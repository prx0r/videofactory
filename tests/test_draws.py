"""Unit tests for sleepdraws (synthetic assets only — no production data).

Entry always fades in from white; clearing is fade to white or instant cut.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'builders'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'contract'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

from PIL import Image, ImageDraw
import holds as H


def stripe_asset(path):
    im = Image.new('RGB', (400, 200), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 399, 199], outline=(23, 20, 15), width=6)
    d.line([0, 100, 399, 100], fill=(23, 20, 15), width=4)
    im.save(path)


class TestDrawProgress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset = '/tmp/vf_test_stripes.png'
        stripe_asset(cls.asset)
        cls.base = Image.new('RGB', (1920, 1080), (255, 255, 255))

    def test_zero_is_blank(self):
        im = H.draw_progress(self.base, self.asset, 0.0)
        px = im.load()
        dark = sum(1 for x in range(400, 1600, 40) for y in range(200, 700, 40)
                   if sum(px[x, y]) < 300)
        self.assertEqual(dark, 0)

    def test_half_is_grey_midline(self):
        im = H.draw_progress(self.base, self.asset, 0.5)
        px = im.load()
        mid = [sum(px[x, 475]) for x in range(760, 1161, 20)]
        self.assertTrue(any(300 < v < 700 for v in mid))

    def test_complete_matches_fitted_asset(self):
        im = H.draw_progress(self.base, self.asset, 1.0)
        px = im.load()
        dark = sum(1 for x in range(760, 1161, 10) for y in (375, 475, 575)
                   if sum(px[x, y]) < 300)
        self.assertGreater(dark, 30)

    def test_falling_progress_fades_back_out(self):
        # clearing reuses the same opacity ramp in reverse (fade to white)
        a = H.draw_progress(self.base, self.asset, 0.25)
        b = H.draw_progress(self.base, self.asset, 0.75)
        da = sum(sum(px) for px in a.getdata())
        db = sum(sum(px) for px in b.getdata())
        self.assertGreater(da, db)  # less asset = brighter frame

    def test_progress_clamped(self):
        a = H.draw_progress(self.base, self.asset, -2.0)
        b = H.draw_progress(self.base, self.asset, 0.0)
        self.assertEqual(list(a.getdata()), list(b.getdata()))
        c = H.draw_progress(self.base, self.asset, 9.0)
        d = H.draw_progress(self.base, self.asset, 1.0)
        self.assertEqual(list(c.getdata()), list(d.getdata()))

    def test_draw_start_skip(self):
        # Ship mode (owner order 2026-11-06): draw staged onto a live
        # Sanskrit card skips record-only, never crashes (ch14 b989
        # over term:yavat killed the unit twice).
        self.assertIsNone(H.draw_start_skip('b989', 'white'))
        for kind in ['term:yavat', 'verse', 'term-single-verse',
                     'verse-hold:b12', 'stack:key']:
            line = H.draw_start_skip('b989', kind)
            self.assertIsNotNone(line)
            self.assertIn('b989', line)
            self.assertIn(kind, line)
            self.assertIn('SKIPPED', line)
        # the renderer honors it (no assert on staging law anymore)
        import pathlib
        src = pathlib.Path(__file__).parent.joinpath(
            '..', 'core', 'builders', 'build_clip.py').read_text()
        self.assertIn('draw_start_skip', src)
        self.assertNotIn('assert _skind', src)

    def test_draws_spec_validation(self):
        import json
        good = {'b2': {'asset': self.asset, 'complete_bid': 'b9',
                       'clear': 'fade', 'fade': 1.5, 'why': 'test'}}
        import factory_contract as C
        C.validate_schema('draws', good, 'good')
        minimal = {'b2': {'asset': self.asset, 'complete_bid': 'b9', 'why': 'test'}}
        C.validate_schema('draws', minimal, 'minimal (clear defaults cut)')
        for bad, name in [
            ({'b2': {'asset': self.asset, 'complete_bid': 'b9'}}, 'missing why'),
            ({'b2': {'asset': self.asset, 'complete_bid': 'b9', 'clear': 'wipe', 'why': 'x'}},
             'wipe rejected'),
            ({'b2': {'asset': self.asset, 'complete_bid': 'b9', 'clear': 'fade', 'fade': 0, 'why': 'x'}},
             'zero fade rejected'),
        ]:
            with self.assertRaises(Exception, msg=name):
                C.validate_schema('draws', bad, name)


if __name__ == '__main__':
    unittest.main()
