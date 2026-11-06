"""Tests for the shiva script-standardization checker (canon-shape, tts-ready).

Shiva-only by owner order (tantrasara finished/frozen): check() no-ops
on other lanes. Canon = CANONICAL-FLOW.md machine-checkable beats;
TTS-ready = mechanical delivery defects only (list patter, colon beats,
Next: trailers, +/- spellings explicitly exempt — locked below).
"""
import json
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))

import check_canon as CC


def _b(bid, typ, voice, text, section='s'):
    return {'id': bid, 'section': section, 'type': typ, 'voice': voice, 'text': text}


_OP = {'id': 'b_opener', 'section': 'o', 'type': 'opener', 'voice': 'none', 'text': '[bell]'}


class CanonShape(unittest.TestCase):
    def test_b1_must_be_title(self):
        bad = [_OP, _b('b1', 'narration', 'granny', 'hello there')]
        self.assertTrue(any(f['bid'] == 'b1' for f in CC.find_shapes(bad, '01')))

    def test_book_marker_presence(self):
        nobook = [_OP, _b('b1', 'title', 'granny', 'Śiva Sūtras 9.9')]
        self.assertTrue(any('BOOK marker' in f['reason'] or 'marker' in f['reason']
                            for f in CC.find_shapes(nobook, '01')))
        ok = nobook + [_b('b2', 'title', 'granny', 'BOOK IX — SOMETHING')]
        self.assertFalse([f for f in CC.find_shapes(ok, '01') if 'BOOK' in f['reason']])
        wrong = [_OP, _b('b1', 'title', 'granny', 'Śiva Sūtras 9.9'),
                 _b('b2', 'title', 'granny', 'BOOK IX — SOMETHING')]
        self.assertTrue(any('only belongs' in f['reason'] for f in CC.find_shapes(wrong, '09')))

    def test_chant_repeat_rule(self):
        chant = _b('b5', 'verse', 'verse', 'परमेश्वरतावेशदार्ढ्यात् स्वातन्त्र्यभाग् गुरुः ।')
        rep = _b('b6', 'narration', 'granny', 'Parameśvaratāveśadārḍhyāt svātantryabhāg guruḥ.')
        eng = _b('b7', 'narration', 'granny', 'The Lord is free.')
        base = [_OP, _b('b1', 'title', 'granny', 'Śiva Sūtras 9.9')]
        self.assertEqual(CC.find_shapes(base + [chant, rep, eng], '99'), [])
        missing = CC.find_shapes(base + [chant, eng], '99')
        self.assertEqual([f['bid'] for f in missing], ['b5'])

    def test_bilingual_self_contained_exempt(self):
        both = _b('b5', 'verse', 'verse', 'अ — A')
        base = [_OP, _b('b1', 'title', 'granny', 'Śiva Sūtras 9.9'), both,
                _b('b6', 'narration', 'granny', 'Next letter.')]
        self.assertEqual(CC.find_shapes(base, '99'), [])

    def test_s00_no_chant(self):
        bad = [_OP, _b('b1', 'title', 'granny', 'The Śiva Sūtras'),
               _b('b2', 'verse', 'verse', 'चैतन्यमात्मा')]
        self.assertTrue(any('never chants' in f['reason'] for f in CC.find_shapes(bad, '00')))


class TtsReady(unittest.TestCase):
    def test_leading_junk_flags(self):
        out = CC.find_tts_ready([_OP, _b('b1', 'narration', 'granny', '-yaḥ — plural ending.')])
        self.assertEqual([f['bid'] for f in out], ['b1'])

    def test_lone_diacritic_flags(self):
        out = CC.find_tts_ready([_OP, _b('b1', 'narration', 'granny', 'ः')])
        self.assertEqual([f['bid'] for f in out], ['b1'])

    def test_embedded_label_flags(self):
        out = CC.find_tts_ready([_OP, _b('b1', 'narration', 'granny',
                                         'final verse\nORIGINAL SANSKRIT')])
        self.assertEqual([f['bid'] for f in out], ['b1'])

    def test_exemptions_hold(self):
        blocks = [_OP,
                  _b('b1', 'narration', 'granny', 'Next:'),
                  _b('b2', 'narration', 'granny', 'Sound + touch'),
                  _b('b3', 'narration', 'granny', 'Dhṛti — firmness:'),
                  _b('b4', 'narration', 'granny', 'It ends properly.')]
        self.assertEqual(CC.find_tts_ready(blocks), [])


class LaneGate(unittest.TestCase):
    def test_tantrasara_skipped(self):
        with unittest.mock.patch.object(CC.H, 'lane_for', return_value={'lane': 'tantrasara'}):
            res = CC.check('/home/ubuntu/tantrasara/storyboard_ch16.json')
        self.assertTrue(res.get('skipped'))
        self.assertEqual(res['shapes'], [])
        self.assertEqual(res['hygiene'], [])

    def test_shiva_suffix_fragments_flagged(self):
        for u, bid in (('s65', 'b11'), ('s72', 'b13')):
            res = CC.check(f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_{u}.json')
            self.assertFalse(res.get('skipped'))
            self.assertIn(bid, [f['bid'] for f in res['hygiene']])
            self.assertEqual(res['shapes'], [])

    def test_shiva_canonical_units_green(self):
        for u in ['s00', 's01', 's23', 's33']:
            res = CC.check(f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_{u}.json')
            self.assertEqual(res['shapes'], [], u)
            self.assertEqual(res['hygiene'], [], u)


class Wiring(unittest.TestCase):
    def test_schema_and_registry(self):
        schema = json.load(open(ROOT / 'core' / 'contract' / 'schemas' / 'issues.schema.json'))
        kinds = schema['properties']['issues']['items']['properties']['kind']['enum']
        self.assertIn('canon-shape', kinds)
        self.assertIn('tts-ready', kinds)
        reg = json.load(open(ROOT / 'core' / 'skills' / 'REGISTRY.json'))
        for kind in ('canon-shape', 'tts-ready'):
            self.assertIn(kind, reg['skills'])
            self.assertTrue((ROOT / 'core' / 'skills' / reg['skills'][kind]['file']).exists())

    def test_check_issues_files_canon_kinds_on_s65(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/s65.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s65.json',
                                '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            kinds = {i['kind'] for i in doc['issues']}
            self.assertIn('tts-ready', kinds)

    def test_no_new_kinds_on_tantrasara(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/ch16.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/storyboard_ch16.json', '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            kinds = {i['kind'] for i in doc['issues']}
            self.assertFalse({'canon-shape', 'tts-ready'} & kinds)


if __name__ == '__main__':
    unittest.main()


class ShivaVerseBacklog(unittest.TestCase):
    def test_backfill_maps_keys_to_bids(self):
        import mine_shiva_verse_gloss as M
        blocks = [{'id': 'b_opener', 'section': 'o', 'type': 'opener', 'voice': 'none', 'text': '[bell]'},
                  {'id': 'b1', 'section': 's', 'type': 'title', 'voice': 'granny', 'text': 'Śiva Sūtras 9.9'}]
        self.assertEqual(M.key_of('चैतन्यमात्मा'), 'caitanyamatma')

    def test_positional_mine_needs_strict_canon_run(self):
        import mine_shiva_verse_gloss as M
        chant = {'id': 'b5', 'section': 's', 'type': 'verse', 'voice': 'verse',
                 'text': 'परमेश्वरतावेशदार्ढ्यात् स्वातन्त्र्यभाग् गुरुः ।'}
        rep = {'id': 'b6', 'section': 's', 'type': 'narration', 'voice': 'granny',
               'text': 'Parameśvaratāvadr̥ḍhyāt svātantryabhāg guruḥ.'}
        gloss = {'id': 'b7', 'section': 's', 'type': 'narration', 'voice': 'granny',
                 'text': 'The Lord is free.'}
        base = [{'id': 'b_opener', 'section': 'o', 'type': 'opener', 'voice': 'none', 'text': '[bell]'},
                {'id': 'b1', 'section': 's', 'type': 'title', 'voice': 'granny', 'text': 'Śiva Sūtras 9.9'}]
        # no repeat following -> skipped, nothing mined
        with unittest.mock.patch.object(M.H, 'lane_for', return_value={
                'glossary': '/none', 'verse': '/none'}):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                p = root / 'storyboard_s99.json'
                p.write_text(json.dumps({'title': 'T', 'blocks': base + [chant, gloss],
                                         'validation': {'errors': [], 'warnings': []}}))
                (root / 'glossary_s99.json').write_text('{}')
                (root / 'verse_gloss_s99.json').write_text('{}')
                with unittest.mock.patch.object(
                        M.H, 'lane_for',
                        return_value={'glossary': str(root / 'glossary_s99.json'),
                                      'lane': 'shiva',
                                      'verse': str(root / 'verse_gloss_s99.json')}):
                    import sys
                    sys.path.insert(0, str(ROOT / 'core' / 'builders'))
                    bf, mine, skipped = M.audit_unit(str(p))
        self.assertEqual(mine, [])
        self.assertIn('b5', [b for b, _ in skipped])

    def test_ralph_routes_shiva_verse_gloss_without_confirming(self):
        import sys
        sys.path.insert(0, str(ROOT / 'core' / 'builders'))
        from ralph_loop import fixer_verse_gloss
        n, note = fixer_verse_gloss(
            '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json',
            {'id': 'x', 'kind': 'verse-deva-no-english'})
        self.assertEqual(n, 0)
        self.assertIn('shiva backlog', note)
        self.assertIn('confirms are owner', note)


if __name__ == '__main__':
    unittest.main()


class BookHeaderRule(unittest.TestCase):
    def test_book_units_carry_book_label(self):
        sys.path.insert(0, str(ROOT / 'core'))
        import lane_api as A
        for u, book in [('s01', 'BOOK I'), ('s23', 'BOOK II'), ('s33', 'BOOK III')]:
            sb = json.load(open(f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_{u}.json'))
            name, mod = A.for_path(f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_{u}.json')
            h = mod.header(sb['blocks'], None)
            self.assertTrue(h['ref'], u)
            self.assertTrue(h['title'].startswith(book), (u, h))
            cov = A.covered_title_bids(
                f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_{u}.json', sb['blocks'])
            self.assertIn('b1', cov)
            self.assertEqual(len([b for b in cov if b != 'b1']), 1, (u, cov))

    def test_nonbook_units_have_no_header_title(self):
        sys.path.insert(0, str(ROOT / 'core'))
        import lane_api as A
        sb = json.load(open('/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s02.json'))
        name, mod = A.for_path('/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s02.json')
        h = mod.header(sb['blocks'], None)
        self.assertEqual(h, {'ref': '1.2', 'title': ''})
        self.assertEqual(A.covered_title_bids(
            '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s02.json', sb['blocks']), ['b1'])

    def test_tantrasara_sheets_unchanged(self):
        sys.path.insert(0, str(ROOT / 'core'))
        import lane_api as A
        sb = json.load(open('/home/ubuntu/tantrasara/storyboard_ch16.json'))
        self.assertEqual(A.covered_title_bids(
            '/home/ubuntu/tantrasara/storyboard_ch16.json', sb['blocks']), [])

    def test_sheets_skip_covered_titles(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'render_holds.py'),
                                '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json', tmp],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-800:])
            holds = sorted(f for f in os.listdir(tmp) if f.startswith('hold') and f.endswith('.png'))
            # 33 blocks -> opener + titles(b1,b2 skipped) + verse/narration figures...
            # b1/b2 must not have standalone pages: fewer files than holds-with-titles
            self.assertTrue(os.path.exists(os.path.join(tmp, 'contact_sheet.png')))
            self.assertLess(len(holds), 33)


if __name__ == '__main__':
    unittest.main()
