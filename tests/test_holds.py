"""Unit tests for the hold-type registry + lane-centralized assets."""
import os
import sys
import unittest
import unicodedata

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


class TestAksharaWrapping(unittest.TestCase):
    def test_conjuncts_never_split(self):
        for word in ['क्रमात्', 'शिवः॥', 'देव्या', 'ज्ञानम्', 'विज्ञानम्']:
            parts = H.split_aksharas(word)
            self.assertEqual(''.join(parts), word)
            self.assertFalse(any(p.endswith('\u094d') for p in parts[:-1]),
                             f'split conjunct in {word}: {parts}')
            self.assertFalse(any(p.startswith(('\u0964', '\u0965')) for p in parts),
                             'stranded danda')

    def test_wrap_breaks_only_long_devanagari(self):
        from PIL import Image, ImageDraw, ImageFont
        d = ImageDraw.Draw(Image.new('RGB', (1920, 1080)))
        fnt = ImageFont.truetype(H.FD, 64)
        long_deva = 'आनन्दामृतनिर्भरस्वहृदयानर्घार्घपात्रक्रमात्'
        lines = H.wrap_lines(d, long_deva, fnt, 780)
        self.assertGreater(len(lines), 1, 'long compound must wrap')
        self.assertTrue(all(d.textlength(ln, font=fnt) <= 782 for ln in lines),
                        'every wrapped line must fit the slot')
        self.assertEqual(''.join(lines), long_deva, 'no glyph lost in wrapping')
        # roman text keeps the old behavior (no intra-word breaks)
        long_roman = 'a' * 100
        self.assertEqual(H.wrap_lines(d, long_roman, fnt, 780), [long_roman])

    def test_long_compound_list_renders(self):
        gl = {'k1': {'deva': H.to_deva('Mūlādhārād'), 'gloss': 'from the root',
                     'status': 'confirmed', 'cue_blocks': ['b1']},
              'k2': {'deva': H.to_deva('prasṛtasuvitatanantanāḍyadhvadaṇḍam'), 'gloss': 'staff',
                     'status': 'confirmed', 'cue_blocks': ['b1']},
              'k3': {'deva': H.to_deva('Nāma'), 'gloss': 'name',
                     'status': 'confirmed', 'cue_blocks': ['b1']}}
        # 3-window triangle would previously die with column overflow;
        # akshara wrapping must carry it through.
        H.render_list(['k1', 'k2', 'k3'], gl)


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
