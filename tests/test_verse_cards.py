"""Tests for the verse-card defect detector (owner bugs, tantrasara 16-22).

Bug 1 (verse-deva-no-english): a verse card ships Devanagari with no
English underneath. The detector replays the renderer's own English
decision (confirmed verse_gloss literal/final via verse_match_key, else
confirmed term layers for single chants) — these tests lock that the
checker's decision agrees with the shared holds.render_hold on fixtures,
and stays green on the frozen ch16 span that proved the bug.

Bug 2 (stale-verse-hold): one Sanskrit verse scattered over several
blocks (Deva + roman half + granny/man IAST tail). Key-equality of
adjacent verse blocks is proof (not heuristic); label/tail patterns are
structural. Tests lock each pattern plus the b822-b824 ch16 span.

Anti-cheat notes: no timing estimates anywhere in the detector (spans
and English decisions are textual + key-based). The parity tests render
with the REAL holds.render_hold (the single implementation sheets and
video share) and assert image-level agreement with card_english, so a
renderer change that alters English layering breaks these tests instead
of silently desyncing the checker.
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))

import check_verse_cards as VC
import holds as H


def _verse(bid, text, voice='verse'):
    return {'id': bid, 'section': 's', 'type': 'verse', 'voice': voice, 'text': text}


def _narr(bid, text, voice='granny'):
    return {'id': bid, 'section': 's', 'type': 'narration', 'voice': voice, 'text': text}


DEVA_FULL = ('परमेश्वरतावेशदार्ढ्यात् स्वातन्त्र्यभाग् गुरुः । '
             'परोक्षमभिसन्धाय दीक्षितेति किमद्भुतम् ॥')
DEVA_KEY = H.verse_match_key(DEVA_FULL)


def _vg_entry(status='confirmed', literal='LIT', final='FIN'):
    return {'bids': ['b9'], 'match_key': DEVA_KEY, 'match_score': 1.0,
            'literal': literal, 'final': final, 'status': status}


def _same_pixels(im1, im2):
    from PIL import ImageChops
    return ImageChops.difference(im1, im2).getbbox() is None


class NoEnglishDecision(unittest.TestCase):
    def test_missing_entry_flags(self):
        b = _verse('b9', DEVA_FULL)
        has, reason = VC.card_english(b, {}, {})
        self.assertFalse(has)
        self.assertIn('no verse_gloss', reason)

    def test_proposed_entry_flags_video_shows_confirmed_only(self):
        b = _verse('b9', DEVA_FULL)
        has, _ = VC.card_english(b, {}, {DEVA_KEY: _vg_entry('proposed')})
        self.assertFalse(has)

    def test_confirmed_entry_clears(self):
        b = _verse('b9', DEVA_FULL)
        has, reason = VC.card_english(b, {}, {DEVA_KEY: _vg_entry('confirmed')})
        self.assertTrue(has)
        self.assertIn('verse_gloss', reason)

    def test_confirmed_empty_layers_flags(self):
        b = _verse('b9', DEVA_FULL)
        has, _ = VC.card_english(b, {}, {DEVA_KEY: _vg_entry('confirmed', '', '')})
        self.assertFalse(has)

    def test_single_confirmed_term_clears(self):
        b = _verse('b7', 'Śaktipāta.')
        gl = {'saktipata': {'deva': 'शक्तिपात', 'gloss': 'descent of power',
                            'literal': '', 'status': 'confirmed'}}
        has, _ = VC.card_english(b, gl, {})
        self.assertTrue(has)

    def test_single_unlisted_term_flags_only_in_split(self):
        b = _verse('b7', 'Kālarātrī.')
        self.assertFalse(VC.card_english(b, {}, {})[0])
        # outside splits it is UNLISTED backlog, not no-english ...
        self.assertEqual(VC.find_no_english([b], {}, {}, set()), [])
        # ... inside a split span it is a half-card with no English
        self.assertEqual(len(VC.find_no_english([b], {}, {}, {'b7'})), 1)

    def test_b2_excluded_tantrasara_only(self):
        b = _verse('b2', DEVA_FULL)
        self.assertEqual(VC.find_no_english([b], {}, {}, set(), 'tantrasara'), [])
        self.assertEqual(len(VC.find_no_english([b], {}, {}, set(), 'shiva')), 1)

    def test_iast_tail_skipped_on_shiva_canon(self):
        blocks = [_verse('b3', DEVA_FULL),
                  _narr('b4', 'Parokṣam abhisandhāya dīkṣiteti kim adbhutam.')]
        self.assertEqual(len(VC.find_split_spans(blocks, 'tantrasara')), 1)
        self.assertEqual(VC.find_split_spans(blocks, 'shiva'), [])


class RendererParity(unittest.TestCase):
    """card_english agrees with the shared holds.render_hold, image-level:
    the renderer is sensitive to a verse_gloss entry iff the checker says
    English is present (confirmed), and ignores proposed entries."""

    def _render(self, block, gl, vg):
        return H.render_hold([block], None, gl, vg, confirmed_only=True)

    def test_renderer_sensitive_iff_checker_says_english(self):
        b = _verse('b9', DEVA_FULL)
        base = self._render(b, {}, {})
        confirmed = self._render(b, {}, {DEVA_KEY: _vg_entry('confirmed')})
        self.assertFalse(_same_pixels(base, confirmed))
        self.assertTrue(VC.card_english(b, {}, {DEVA_KEY: _vg_entry('confirmed')})[0])
        self.assertFalse(VC.card_english(b, {}, {})[0])

    def test_renderer_ignores_proposed_and_checker_agrees(self):
        b = _verse('b9', DEVA_FULL)
        base = self._render(b, {}, {})
        proposed = self._render(b, {}, {DEVA_KEY: _vg_entry('proposed')})
        self.assertTrue(_same_pixels(base, proposed))
        self.assertFalse(VC.card_english(b, {}, {DEVA_KEY: _vg_entry('proposed')})[0])

    def test_single_term_parity(self):
        b = _verse('b7', 'Śaktipāta.')
        gl = {'saktipata': {'deva': 'शक्तिपात', 'gloss': 'descent of power',
                            'literal': '', 'status': 'confirmed'}}
        with_term = self._render(b, gl, {})
        without = self._render(b, {}, {})
        self.assertFalse(_same_pixels(with_term, without))
        self.assertTrue(VC.card_english(b, gl, {})[0])
        self.assertFalse(VC.card_english(b, {}, {})[0])


class SplitSpans(unittest.TestCase):
    def test_label_block_flags(self):
        blocks = [_narr('b1', 'intro'), _verse('b2', 'Ch N'),
                  _verse('b3', DEVA_FULL + '\nTRANSLITERATION')]
        spans = VC.find_split_spans(blocks)
        self.assertEqual(len(spans), 1)
        self.assertIn('split-label', spans[0]['patterns'])

    def test_iaST_label_variant_flags(self):
        blocks = [_verse('b3', DEVA_FULL + '\nIAST TRANSLITERATION')]
        spans = VC.find_split_spans(blocks)
        self.assertEqual(len(spans), 1)

    def test_equal_key_pair_is_proof(self):
        half_deva = 'ततः परमशिवे योजनिकां कृत्वा'
        half_roman = 'Tataḥ paramaśive yojanikāṃ kṛtvā.'
        self.assertEqual(H.verse_match_key(half_deva), H.verse_match_key(half_roman))
        blocks = [_verse('b3', half_deva), _verse('b4', half_roman)]
        spans = VC.find_split_spans(blocks)
        self.assertEqual([s['bids'] for s in spans], [['b3', 'b4']])
        self.assertIn('same-key-pair', spans[0]['patterns'])

    def test_pure_single_pair_excluded_from_check(self):
        # two one-word term chants: re-chants, not splits — neither
        # find_split_spans nor check() reports them (they stay under
        # glossary/audit discipline).
        blocks = [_narr('b1', 'x'), _verse('b2', 'Ch N'),
                  _verse('b3', 'Śeṣa.'), _verse('b4', 'शेष'),
                  _narr('b5', 'What remains.')]
        self.assertEqual(VC.find_split_spans(blocks), [])
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb = {'title': 'T', 'blocks': [{'id': 'b_opener', 'section': 'o', 'type': 'opener',
                                            'voice': 'none', 'text': '[bell]'}] + blocks,
                  'validation': {'errors': [], 'warnings': []}}
            (root / 'storyboard_ch01.json').write_text(json.dumps(sb, ensure_ascii=False))
            (root / 'glossary_ch01.json').write_text(json.dumps({}))
            (root / 'verse_gloss_ch01.json').write_text(json.dumps({}))
            import unittest.mock as mock
            with mock.patch.object(VC._H, 'lane_for', return_value={
                    'glossary': str(root / 'glossary_ch01.json'),
                    'verse': str(root / 'verse_gloss_ch01.json')}):
                res = VC.check(str(root / 'storyboard_ch01.json'))
        self.assertEqual(res['spans'], [])

    def test_iast_tail_flags_and_chains(self):
        blocks = [_verse('b3', DEVA_FULL),
                  _narr('b4', 'Parokṣam abhisandhāya dīkṣiteti kim adbhutam.'),
                  _narr('b5', 'Vināpi jñāna-yogābhyāṃ caryā-mātreṇa mucyate.')]
        spans = VC.find_split_spans(blocks)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]['bids'], ['b4', 'b5'])
        self.assertIn('iast-tail-misvoiced', spans[0]['patterns'])

    def test_english_commentary_not_a_tail(self):
        blocks = [_verse('b3', DEVA_FULL),
                  _narr('b4', 'Thus all the regular activities have been explained.')]
        self.assertEqual(VC.find_split_spans(blocks), [])


class RealData(unittest.TestCase):
    def test_ch16_b822_span_exact(self):
        sb = json.load(open('/home/ubuntu/tantrasara/storyboard_ch16.json', encoding='utf-8'))
        spans = [s for s in VC.find_split_spans(sb['blocks'])
                 if 'b822' in s['bids']]
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]['bids'], ['b822', 'b823', 'b824'])
        self.assertEqual(set(spans[0]['patterns']),
                         {'split-label', 'roman-only-verse', 'iast-tail-misvoiced'})

    def test_ch16_no_english_contains_label_polluted_key(self):
        res = VC.check('/home/ubuntu/tantrasara/storyboard_ch16.json')
        bids = {f['bid'] for f in res['no_english']}
        # b822's key carries the TRANSLITERATION label word, so no
        # full-verse gloss entry can ever match it — structural, survives
        # scholar mining of other verses.
        self.assertIn('b822', bids)
        self.assertNotIn('b2', bids)

    def test_all_findings_reference_real_bids(self):
        for ch in ['16', '17', '18', '19', '20', '21', '22']:
            sb = json.load(open(f'/home/ubuntu/tantrasara/storyboard_ch{ch}.json', encoding='utf-8'))
            ids = {b['id'] for b in sb['blocks']}
            res = VC.check(f'/home/ubuntu/tantrasara/storyboard_ch{ch}.json')
            for f in res['no_english']:
                self.assertIn(f['bid'], ids)
            for sp in res['spans']:
                for bid in sp['bids']:
                    self.assertIn(bid, ids)

    def test_schema_and_registry_cover_new_kinds(self):
        schema = json.load(open(ROOT / 'core' / 'contract' / 'schemas' / 'issues.schema.json'))
        kinds = schema['properties']['issues']['items']['properties']['kind']['enum']
        self.assertIn('verse-deva-no-english', kinds)
        self.assertIn('stale-verse-hold', kinds)
        reg = json.load(open(ROOT / 'core' / 'skills' / 'REGISTRY.json'))
        for kind in ('verse-deva-no-english', 'stale-verse-hold'):
            self.assertIn(kind, reg['skills'])
            self.assertTrue((ROOT / 'core' / 'skills' / reg['skills'][kind]['file']).exists())

    def test_check_issues_files_new_kinds_on_ch16(self):
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
            self.assertIn('verse-deva-no-english', kinds)
            self.assertIn('stale-verse-hold', kinds)
            reg = json.loads(open(str(ROOT / 'core' / 'skills' / 'REGISTRY.json')).read())
            for i in doc['issues']:
                self.assertIn(i['skill'], reg['skills'])


if __name__ == '__main__':
    unittest.main()
