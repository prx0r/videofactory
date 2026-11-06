"""Tests for the stack-crash predictor (ch16 p02 build-killer precedent).

build_clip fires EVERY matching word as a cue (its word-row loop defeats
the documented one-cue-per-block rule), so one block chanting several
long compounds forms a same-block run that collides in render_list and
dies mid-render — which the one-per-block entry gate cannot see coming.
check_stacks.py replays the renderer cue rule with the REAL render_list,
part-aware (cross-part runs never co-render).

Anti-cheat notes: collision is decided by the shared holds.render_list
(same call build_clip makes); cue keys via shared fold/to_iast;
part ranges replicate run_blocks chunking via shared split helpers.
The ch16 test locks the exact crashing keys from the real build log.
"""
import json
import os
import re
import sys
import unittest
import unittest.mock
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))

import check_stacks as CS
import holds as H


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


LONG_1 = 'prasṛta-suvitatānanta-nāḍyadhva-daṇḍam'
LONG_2 = 'nāsā-gagana-parigataṃ'
LONG_3 = 'dhūmābhirāma-pracitatara-śikhā-jālakena'


def _gl_for(*words):
    gl = {}
    for w in words:
        k = _fold(w.strip('.,!?;:\'"—-'))
        gl[k] = {'deva': H.to_deva(w.strip('.,!?;:\'"—-')), 'gloss': f'gloss of {k}',
                 'literal': '', 'status': 'confirmed'}
    return gl


def _blocks(spec):
    out = [{'id': 'b_opener', 'section': 'o', 'type': 'opener',
            'voice': 'none', 'text': '[bell]'}]
    for bid, typ, voice, text in spec:
        out.append({'id': bid, 'section': 's', 'type': typ, 'voice': voice, 'text': text})
    return out


class StackPredictor(unittest.TestCase):
    def test_same_block_multi_cue_run_collides(self):
        # one narration block chanting three giant compounds: renderer fires
        # 3 cues (one per matching word) forming a run that cannot fit.
        text = f'Mūlādhārād udetya {LONG_1} vīryeṇākramya {LONG_2} vikṣipan.'
        blocks = _blocks([('b1', 'narration', 'granny', 'intro words here'),
                          ('b2', 'narration', 'granny', text)])
        gl = _gl_for('Mūlādhārād', LONG_1, LONG_2)
        # drive predict() on a synthetic storyboard via temp files
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb_path = root / 'storyboard_ch01.json'
            sb_path.write_text(json.dumps({'title': 'T', 'blocks': blocks,
                                           'validation': {'errors': [], 'warnings': []}}))
            (root / 'glossary_ch01.json').write_text(json.dumps(
                {k: dict(v, status='confirmed') for k, v in gl.items()}))
            with unittest.mock.patch.object(CS.H, 'lane_for', return_value={
                    'glossary': str(root / 'glossary_ch01.json'), 'verse': None,
                    'drops': str(root / 'drops_ch01.json')}):
                res = CS.predict(str(sb_path))
        self.assertEqual(len(res), 1)
        self.assertIn('muladharad', res[0]['keys'])

    def test_events_break_runs(self):
        # same cues separated by a verse block (an event): no run, no crash.
        verse = 'Mūlādhārād udetya.'
        blocks = _blocks([('b1', 'narration', 'granny', f'{LONG_1} here'),
                          ('b2', 'verse', 'verse', verse),
                          ('b3', 'narration', 'granny', f'{LONG_2} there')])
        gl = _gl_for(LONG_1, LONG_2)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb_path = root / 'storyboard_ch01.json'
            sb_path.write_text(json.dumps({'title': 'T', 'blocks': blocks,
                                           'validation': {'errors': [], 'warnings': []}}))
            (root / 'glossary_ch01.json').write_text(json.dumps(
                {k: dict(v, status='confirmed') for k, v in gl.items()}))
            with unittest.mock.patch.object(CS.H, 'lane_for', return_value={
                    'glossary': str(root / 'glossary_ch01.json'), 'verse': None,
                    'drops': str(root / 'drops_ch01.json')}):
                res = CS.predict(str(sb_path))
        self.assertEqual(res, [])

    def test_cross_part_runs_ignored(self):
        # two cue blocks in DIFFERENT parts but one estimated run (section
        # change splits groups/parts, but sections are not events so the
        # chain still forms): cross-part runs never co-render — ignored.
        filler = ('filler words here. ' * 600).strip()
        blocks = [{'id': 'b_opener', 'section': 'o', 'type': 'opener',
                   'voice': 'none', 'text': '[bell]'},
                  {'id': 'b1', 'section': 's1', 'type': 'narration',
                   'voice': 'granny', 'text': 'Mūlādhārād rises.'},
                  {'id': 'b2', 'section': 's2', 'type': 'narration',
                   'voice': 'granny', 'text': filler},
                  {'id': 'b3', 'section': 's2', 'type': 'narration',
                   'voice': 'granny', 'text': 'Nāsā-gagana follow.'}]
        gl = _gl_for('Mūlādhārād', 'Nāsā-gagana')
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb_path = root / 'storyboard_ch01.json'
            sb_path.write_text(json.dumps({'title': 'T', 'blocks': blocks,
                                           'validation': {'errors': [], 'warnings': []}}))
            (root / 'glossary_ch01.json').write_text(json.dumps(
                {k: dict(v, status='confirmed') for k, v in gl.items()}))
            with unittest.mock.patch.object(CS.H, 'lane_for', return_value={
                    'glossary': str(root / 'glossary_ch01.json'), 'verse': None,
                    'drops': str(root / 'drops_ch01.json')}):
                ranges = CS.part_ranges(json.loads(sb_path.read_text())['blocks'], str(sb_path))
                self.assertTrue(len(ranges) >= 2)  # filler forces a split
                res = CS.predict(str(sb_path))
        self.assertEqual(res, [])

    def test_ch16_exact_crash_keys(self):
        res = CS.predict('/home/ubuntu/tantrasara/storyboard_ch16.json')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['bids'], ['b317'])
        self.assertEqual(res[0]['keys'][:3],
                         ['muladharad', 'prasrta-suvitatananta-nadyadhva-dandam',
                          'nasa-gagana-parigatam'])

    def test_ch20_devya_run_renderer_would_build(self):
        # ch20 audio-gated on H-list (preflight worst-case-5, same FP class
        # as the fixed ch21 one). Independently of that gate, the renderer
        # would crash on this real multi-cue run (b567->b568, adjacent
        # blocks, no event between) — so fixing the gate alone is not
        # enough; the list needs the owner restyle first.
        res = CS.predict('/home/ubuntu/tantrasara/storyboard_ch20.json')
        by_bids = {tuple(r['bids']): r['keys'] for r in res}
        self.assertIn(('b567', 'b568'), by_bids)
        self.assertEqual(by_bids[('b567', 'b568')][:3],
                         ['devya', 'anandamrta-nirbhara-svahrdayanargharghapatra-kramat', 'tvam'])

    def test_factory_gate_passes_ch20_documents_divergence(self):
        # The run-based factory gate does not see ch20's crash run (its
        # one-cue-per-block model stops at b568's first match, missing the
        # tvam cue that tips the stack over). This test locks the
        # divergence: post-drain the gates unify on multi-cue runs.
        import factory_contract as C
        self.assertTrue(C.require_list_geometry('/home/ubuntu/tantrasara/storyboard_ch20.json'))

    def test_ch12_current_data_flags_future_rebuild(self):
        # shipped ch12 predates its confirms; current data would crash a
        # rebuild — the checker evaluates what a launch would face.
        res = CS.predict('/home/ubuntu/tantrasara/storyboard_ch12.json')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['bids'], ['b224', 'b242', 'b250'])

    def test_rendered_units_clean(self):
        for ch in ['01', '02', '03', '04', '05', '07', '08', '09', '10',
                   '11', '13', '14', '15', '17', '18', '19', '21', '22']:
            sb = f'/home/ubuntu/tantrasara/storyboard_ch{ch}.json'
            with self.subTest(ch=ch):
                self.assertEqual(CS.predict(sb), [])

    def test_schema_and_registry_cover_stack_crash(self):
        schema = json.load(open(ROOT / 'core' / 'contract' / 'schemas' / 'issues.schema.json'))
        self.assertIn('stack-crash', schema['properties']['issues']['items']['properties']['kind']['enum'])
        reg = json.load(open(ROOT / 'core' / 'skills' / 'REGISTRY.json'))
        self.assertIn('stack-crash', reg['skills'])
        self.assertTrue((ROOT / 'core' / 'skills' / reg['skills']['stack-crash']['file']).exists())

    def test_stack_crash_retired_from_runtime(self):
        # The renderer now fires ONE cue per block, so same-block multi-cue
        # runs cannot form; the predictor is a forensic tool, not a gate.
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/ch16.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/storyboard_ch16.json', '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            self.assertEqual([i for i in doc['issues'] if i['kind'] == 'stack-crash'], [])

    def test_ralph_loop_handles_new_kinds_dry_run(self):
        # autonomy wiring proof: the loop routes every open kind on ch16
        # (verse-deva-no-english, stale-verse-hold, stack-crash, draws...)
        # to fixer-or-blocked with a skill pointer — never an exception.
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                [sys.executable, str(ROOT / 'core' / 'builders' / 'ralph_loop.py'),
                 '--project', 'tantrasara', '--units', '16', '--max-iters', '1',
                 '--dry-run', '--out', f'{tmp}/ralph.json', '--issues-dir', tmp],
                capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[-800:])
            rep = json.loads(open(f'{tmp}/ralph.json').read())
            kinds = {b['kind'] for u in rep['units'] for b in u['blocked']}
            self.assertTrue({'verse-deva-no-english', 'stale-verse-hold'} <= kinds)
            for u in rep['units']:
                for b in u['blocked']:
                    self.assertTrue(b['skill'])


if __name__ == '__main__':
    unittest.main()
