"""Unit tests for the hold-type registry + lane-centralized assets."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'builders'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'contract'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import holds as H
import paths as _vf


def colophon_card(d, im, hold, sub_text, glossary):
    fnt = H.F(H.FE, 44)
    H.ct(d, 400, 'colophon line', fnt)
    H.assert_safe(450, 'colophon')


class TestRegistry(unittest.TestCase):
    def test_core_kinds_not_overridable(self):
        for kind in ('opener', 'title', 'figure', 'verse'):
            with self.assertRaises(ValueError):
                H.register_hold(kind, colophon_card)

    def test_custom_kind_renders_with_subtitle_footer(self):
        H.register_hold('colophon', colophon_card)
        try:
            hold = [{'id': 'b1', 'section': 'body', 'type': 'colophon',
                     'voice': 'granny', 'text': 'Colophon words here.'}]
            im = H.render_hold(hold, sub_text='spoken line here', glossary={})
            self.assertEqual(im.size, (1920, 1080))
        finally:
            del H._HOLD_RENDERERS['colophon']

    def test_assert_safe_trips(self):
        with self.assertRaises(AssertionError):
            H.assert_safe(900, 'test')


class TestCentralizedAssets(unittest.TestCase):
    def test_voices_default_to_frozen_seats(self):
        v = _vf.voices()
        self.assertEqual(v['granny'], '614f8afd83f841048c040b2c6234d2c1')
        self.assertEqual(v['man'], 'fcfd5ebf496949ed9f76b3a533ee4738')
        self.assertEqual(v['verse'], '4e873c37d4cb439e9bccc4dc1f633290')

    def test_series_config_wins(self):
        import json
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'projects', 'tantrasara', 'project.json')
        cfg = json.load(open(cfg_path, encoding='utf-8'))
        self.assertEqual(set(cfg['voices']), {'granny', 'man', 'verse'})
        self.assertEqual(_vf.voices(), cfg['voices'])

    def test_font_faces_resolve(self):
        f = _vf.fonts()
        for k in ('deva', 'gloss', 'subtitle'):
            self.assertTrue(os.path.exists(f[k]), f'missing face {k}: {f[k]}')

    def test_tts_bell_phonemes_resolve(self):
        self.assertTrue(os.path.exists(_vf.tts_script()), 'tts_line.py missing')
        self.assertTrue(os.path.exists(_vf.bell()), 'bell wav missing')
        self.assertTrue(os.path.isdir(_vf.phoneme_dir()), 'phoneme clips missing')


if __name__ == '__main__':
    unittest.main()
