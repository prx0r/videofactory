"""Regression tests for the tantrasara ch14-22 postmortem.

Each test names the bug it locks out:
- ch16/17/19/20/22: bulk-confirm flipped empty-gloss + machine-lossy Deva to
  confirmed; strict prove died after hours of video. Factory must fail at
  validate_bundle (entry), never after video.
- ch15/21: 'conveyor collides with subtitle zone' killed video hours in.
  Factory must fail at list-geometry gate (headless images, no audio/video).
- ch18 b340: 'missing render' killed video mid-range. Factory must fail at
  audio-complete gate before video.
- compat debt: video gates logged FAIL but continued; prove raised later.
  Factory default must be strict.
- mine_glossary: full-lane remine overwrote series glossaries. Factory miner
  must write to proposed/, never the series repo by default.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))
sys.path.insert(0, str(ROOT / 'core'))

import factory_contract as C
import gates


def _fixture(tmp, gl_patch=None):
    sb_path = Path(tmp) / 'storyboard_ch01.json'
    gl_path = Path(tmp) / 'glossary_ch01.json'
    ap_path = Path(tmp) / 'approved_ch01.json'
    opener = {'id': 'b_opener', 'section': 'opener', 'type': 'opener',
              'voice': 'none', 'text': '[bell]', 'asset': '/tmp/bell.wav', 'mix': '+6dB'}
    blocks = [opener,
              {'id': 'b1', 'section': 'body', 'type': 'narration', 'voice': 'granny',
               'text': 'Opening words here now.', 'directed': 'Opening words here now.'},
              {'id': 'b2', 'section': 'body', 'type': 'verse', 'voice': 'verse',
               'text': 'शिवः', 'directed': 'शिवः'}]
    sb_path.write_text(json.dumps({'title': 'Test chapter', 'blocks': blocks,
                                   'validation': {'errors': [], 'warnings': []}}), encoding='utf-8')
    gl = {'siva': {'deva': 'शिवः', 'gloss': 'Śiva', 'status': 'confirmed', 'cue_blocks': ['b1']}}
    if gl_patch:
        gl_patch(gl)
    gl_path.write_text(json.dumps(gl, ensure_ascii=False), encoding='utf-8')
    ap_path.write_text(json.dumps({'date': '2026-11-04', 'storyboard_sha': C.sha256(sb_path),
                                   'glossary_sha': C.sha256(gl_path), 'note': 'test'}), encoding='utf-8')
    return sb_path


class PostmortemLocks(unittest.TestCase):
    def test_confirmed_empty_gloss_never_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            sb = _fixture(tmp, lambda gl: gl.update(
                {'emptyterm': {'deva': 'शिवः', 'gloss': '', 'status': 'confirmed', 'cue_blocks': ['b1']}}))
            # schema ('does not match') or explicit ('empty gloss') — either
            # must block; the bug was bulk-confirm passing this data.
            with self.assertRaises(C.ContractError):
                C.validate_bundle(sb)

    def test_confirmed_machine_deva_never_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            def patch(gl):
                gl['siva']['deva_status'] = 'machine-lossy'
            sb = _fixture(tmp, patch)
            with self.assertRaisesRegex(C.ContractError, 'machine-lossy'):
                C.validate_bundle(sb)

    def test_gates_default_is_strict(self):
        old = os.environ.pop('VF_GATES', None)
        try:
            self.assertEqual(gates.mode(), 'strict')
            # compat still available as explicit opt-in, but never default
            os.environ['VF_GATES'] = 'compat'
            self.assertEqual(gates.mode(), 'compat')
        finally:
            if old is not None:
                os.environ['VF_GATES'] = old
            else:
                os.environ.pop('VF_GATES', None)

    def test_list_geometry_gate_catches_overflow_before_video(self):
        import holds as H
        # Five long-gloss terms overflow the bottom slots (ch15/21 shape).
        gl = {f'term{i}': {'deva': 'शिवः', 'gloss': 'word ' * 40, 'status': 'confirmed',
                           'cue_blocks': ['b1']} for i in range(5)}
        with self.assertRaises(AssertionError):
            H.render_list(list(gl)[:5], gl)
        # preflight surfaces the same failure headlessly with keys attached
        with self.assertRaises(ValueError):
            H.preflight_list_geometry(gl)

    def test_audio_complete_gate_names_missing_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            sb = _fixture(tmp)
            with self.assertRaisesRegex(C.ContractError, 'missing audio|no spoken|audio-complete|missing audio render'):
                C.require_audio_complete(sb, ['b1'])

    def test_mine_glossary_defaults_to_proposed_never_series(self):
        import mine_glossary as _mg
        import inspect
        src = inspect.getsource(_mg.main)
        self.assertIn('proposed', src)
        self.assertIn('refusing to overwrite series glossaries', src)

    def test_verse_chant_fires_term_cue(self):
        # Śaktipāta. chanted by verse must hold as a term card after the
        # chant (postmortem fix) — scan must list it as a verse-term hold.
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'scan_holds.py'),
                            '/home/ubuntu/tantrasara/storyboard_ch15.json'],
                           capture_output=True, text=True)
        self.assertIn('verse-term holds', r.stdout)
        self.assertIn('saktipata', r.stdout)

    def test_hold_scan_fails_past_60s_with_reasoning(self):
        import subprocess
        r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'scan_holds.py'),
                            '/home/ubuntu/tantrasara/storyboard_ch21.json', '--max', '60'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('SCAN RED', r.stdout)
        # reasoning attached: stuck term needs draw, or verse-term path named
        self.assertTrue('needs draw' in r.stdout or 'fixed path' in r.stdout or 'WHITE_GAP' in r.stdout)

    def test_issue_skill_loop_emits_valid_issues_with_skills(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/ch15.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/storyboard_ch15.json', '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            import sys as _sys
            _sys.path.insert(0, str(ROOT / 'core' / 'contract'))
            import factory_contract as _C
            _C.validate_schema('issues', doc, out)
            kinds = {i['kind'] for i in doc['issues']}
            # machine-deva/empty-gloss are fixed for ch15 (round-trip verified
            # / T1-filled / proposed-flipped) — what remains is draw + scholar
            # work, each naming its skill:
            self.assertTrue(kinds)
            self.assertTrue(kinds <= {'verse-gloss-missing', 'verse-deva-no-english', 'stale-verse-hold',
                                       'stack-crash', 'white-gap', 'stuck-term',
                                       'empty-gloss', 'machine-deva', 'missing-audio',
                                       'list-geometry', 'hold-scan-red'})
            # every issue names a registered skill
            reg = json.loads(open(str(ROOT / 'core' / 'skills' / 'REGISTRY.json')).read())
            for i in doc['issues']:
                self.assertIn(i['skill'], reg['skills'])
            # verse-gloss backfill loop (solved 2026-11-06): ch15 mined entry
            # exists and is confirmed; b2 (chapter-name chant) is excluded
            vg = json.loads(open('/home/ubuntu/tantrasara/verse_gloss_ch15.json').read())
            self.assertIn('abhts_15.1', vg)
            self.assertEqual(vg['abhts_15.1']['status'], 'confirmed')
            vgm = [i for i in doc['issues'] if i['kind'] == 'verse-gloss-missing']
            self.assertTrue(vgm)
            self.assertNotIn('b2', vgm[0]['blocks'])

    def test_waivers_release_waived_issues(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/ch15.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/storyboard_ch15.json', '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            target = next(i for i in doc['issues'] if i['severity'] in ('block', 'needs-owner'))
            json.dump({'version': 1, 'waived': [target['id']],
                       'reason': 'test waiver', 'date': '2026-11-06'},
                      open(f'{tmp}/ch15.waivers.json', 'w'))
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/storyboard_ch15.json', '--out', out],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            doc = json.loads(open(out).read())
            self.assertEqual(next(i for i in doc['issues'] if i['id'] == target['id'])['status'], 'waived-owner')

    def test_batch_runs_issues_first(self):
        import batch
        self.assertEqual(batch.STAGES[0], 'issues')

    def test_gate_feeds_renderer_identical_inputs(self):
        # The gate must mirror build_clip's _gl exactly (confirmed + gloss,
        # literal only when literal_status is confirmed). An unconfirmed
        # literal must never widen a card in the gate.
        import shutil
        import holds as H
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, 'lit')
            os.makedirs(root)
            fat = 'The Authority of Scripture with a great deal of extra words to be certain it wraps'
            sb = {'title': 'T', 'blocks': [
                {'id': 'b_opener', 'section': 'o', 'type': 'opener', 'voice': 'none',
                 'text': '[bell]', 'asset': '/tmp/bell.wav', 'mix': '+6dB'},
                {'id': 'b1', 'section': 's', 'type': 'narration', 'voice': 'granny',
                 'text': 'alpha Beta gamma', 'directed': 'alpha Beta gamma'},
                {'id': 'b2', 'section': 's', 'type': 'narration', 'voice': 'granny',
                 'text': 'delta Epsilon zeta', 'directed': 'delta Epsilon zeta'}],
                'validation': {'errors': [], 'warnings': []}}
            gl = {
                'beta': {'deva': H.to_deva('Beta'), 'gloss': 'second', 'status': 'confirmed',
                         'cue_blocks': ['b1'], 'literal': 'unconfirmed literal that would collide ' * 6,
                         'literal_status': 'proposed'},
                'epsilon': {'deva': H.to_deva('Epsilon'), 'gloss': 'fifth', 'status': 'confirmed',
                            'cue_blocks': ['b2']},
            }
            json.dump(sb, open(os.path.join(root, 'storyboard_ch01.json'), 'w'), ensure_ascii=False)
            json.dump(gl, open(os.path.join(root, 'glossary_ch01.json'), 'w'), ensure_ascii=False)
            # passes: renderer drops the proposed literal, so must the gate
            C.require_list_geometry(os.path.join(root, 'storyboard_ch01.json'))

    def test_geometry_gate_mirrors_renderer_runs(self):
        # Akshara wrapping fixed the width class (long Devas now wrap and
        # fit) — the gate must still catch what wrapping cannot fix: a
        # triangle run whose bottom-slot card is too TALL (dense literal +
        # gloss under a wrapped Deva overflows the subtitle zone).
        import shutil
        import holds as H
        import unicodedata as _ud

        def key_of(s):
            return re.sub(r'[^a-z0-9]+', '', ''.join(
                c for c in _ud.normalize('NFD', s.lower()) if _ud.category(c) != 'Mn'))

        with tempfile.TemporaryDirectory() as tmp:
            # control: short terms everywhere render fine
            root = os.path.join(tmp, 'ok')
            os.makedirs(root)
            blocks = [{'id': 'b_opener', 'section': 'o', 'type': 'opener',
                       'voice': 'none', 'text': '[bell]',
                       'asset': '/tmp/bell.wav', 'mix': '+6dB'}]
            gl = {}
            for i, s in enumerate(['Śivaḥ', 'Devyā', 'Agniḥ'], 1):
                blocks.append({'id': f'b{i}', 'section': 's', 'type': 'narration',
                               'voice': 'granny', 'text': f'alpha {s} omega',
                               'directed': f'alpha {s} omega'})
                gl[key_of(s)] = {'deva': H.to_deva(s), 'gloss': f'gloss {i}',
                                 'status': 'confirmed', 'cue_blocks': [f'b{i}']}
            json.dump({'title': 'T', 'blocks': blocks,
                       'validation': {'errors': [], 'warnings': []}},
                      open(os.path.join(root, 'storyboard_ch01.json'), 'w'), ensure_ascii=False)
            json.dump(gl, open(os.path.join(root, 'glossary_ch01.json'), 'w'), ensure_ascii=False)
            C.require_list_geometry(os.path.join(root, 'storyboard_ch01.json'))
            # genuine overflow: long wrapped Deva + IAST + confirmed long
            # literal + gloss cannot fit a triangle bottom slot (y=620..860)
            root = os.path.join(tmp, 'tall')
            os.makedirs(root)
            blocks = [{'id': 'b_opener', 'section': 'o', 'type': 'opener',
                       'voice': 'none', 'text': '[bell]',
                       'asset': '/tmp/bell.wav', 'mix': '+6dB'}]
            gl = {}
            terms = [('Alphaḥ', 'first word here'), ('Beta', 'second word here'),
                     ('Ānandāmṛtanirbharasvahṛdayānarghyārghyapātrakramāt',
                      'vessel of bliss nectar full of itself and everything else besides')]
            for i, (s, g) in enumerate(terms, 1):
                blocks.append({'id': f'b{i}', 'section': 's', 'type': 'narration',
                               'voice': 'granny', 'text': f'alpha {s} omega',
                               'directed': f'alpha {s} omega'})
                gl[key_of(s)] = {'deva': H.to_deva(s), 'gloss': g, 'status': 'confirmed',
                                 'cue_blocks': [f'b{i}']}
            json.dump({'title': 'T', 'blocks': blocks,
                       'validation': {'errors': [], 'warnings': []}},
                      open(os.path.join(root, 'storyboard_ch01.json'), 'w'), ensure_ascii=False)
            json.dump(gl, open(os.path.join(root, 'glossary_ch01.json'), 'w'), ensure_ascii=False)
            with self.assertRaisesRegex(C.ContractError, 'run'):
                C.require_list_geometry(os.path.join(root, 'storyboard_ch01.json'))

    def test_check_issues_unit_is_lane_aware(self):
        # shiva units resolve to sNN, never the tantrasara chNN fallback.
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/s01.issues.json'
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                                '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json',
                                '--out', out],
                               capture_output=True, text=True, check=True)
            doc = json.load(open(out))
            self.assertEqual(doc['unit'], 's01')
            import factory_contract as _C
            _C.validate_schema('issues', doc, out)

    def test_batch_validates_ship_before_voices(self):
        import batch
        self.assertIn('validate', batch.STAGES)
        self.assertLess(batch.STAGES.index('verify'), batch.STAGES.index('validate'))
        self.assertLess(batch.STAGES.index('validate'), batch.STAGES.index('voices'))
        self.assertLess(batch.STAGES.index('validate'), batch.STAGES.index('ship'))

    def test_require_issues_clear_blocks_and_waives(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            out = f'{tmp}/ch15.issues.json'
            subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'check_issues.py'),
                            '/home/ubuntu/tantrasara/storyboard_ch15.json', '--out', out],
                           capture_output=True, text=True, check=True)
            # ch15 carries verse-deva-no-english (b234/b509 below-threshold
            # scholar backlog — the never-again gate): open needs-owner
            # issues block launch until waived or scholar-paired.
            with self.assertRaisesRegex(C.ContractError, 'verse-deva-no-english'):
                C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp)
            doc = json.load(open(out))
            waive_all = [i['id'] for i in doc['issues'] if i['status'] == 'open'
                         and i['severity'] in ('block', 'needs-owner')]
            self.assertTrue(waive_all)
            json.dump({'version': 1, 'waived': waive_all,
                       'reason': 'test waiver', 'date': '2026-11-06'},
                      open(f'{tmp}/ch15.waivers.json', 'w'))
            self.assertTrue(C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp))
            os.remove(f'{tmp}/ch15.waivers.json')
            # synthetic blocker proves the gate mechanics: raise naming skill,
            # waive to pass, draws-only passes, absent passes.
            doc = json.load(open(out))
            doc['issues'].append({'id': 'machine-deva-9', 'kind': 'machine-deva', 'severity': 'needs-owner',
                                  'detail': 'synthetic blocker', 'blocks': [], 'skill': 'machine-deva',
                                  'status': 'open', 'resolution_note': ''})
            json.dump(doc, open(out, 'w'))
            with self.assertRaisesRegex(C.ContractError, 'core/skills/'):
                C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp)
            # needs-draw-only doc never blocks launch (hold-scan owns it)
            only_draws = {'version': 1, 'unit': '15',
                          'storyboard_sha256': C.sha256('/home/ubuntu/tantrasara/storyboard_ch15.json'),
                          'issues': [{'id': 'white-gap-1', 'kind': 'white-gap', 'severity': 'needs-draw',
                                      'detail': 'test gap', 'blocks': ['b1'], 'skill': 'white-gap',
                                      'status': 'open', 'resolution_note': ''}]}
            json.dump(only_draws, open(out, 'w'))
            self.assertTrue(C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp))
            # missing-audio never blocks launch (batch audio stage renders
            # it; video entry enforces completeness)
            only_draws['issues'].append({'id': 'missing-audio-1', 'kind': 'missing-audio', 'severity': 'block',
                                         'detail': 'synthetic gap', 'blocks': ['b1'], 'skill': 'missing-audio',
                                         'status': 'open', 'resolution_note': ''})
            json.dump(only_draws, open(out, 'w'))
            self.assertTrue(C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp))
            # absent file passes (checker has not run)
            os.remove(out)
            self.assertTrue(C.require_issues_clear('/home/ubuntu/tantrasara/storyboard_ch15.json', tmp))

    def test_refresh_never_blocks_on_issues(self):
        # Owner order 2026-11-06: issues are a work list, never a gate.
        # A unit with an open needs-owner issue stays approved-ready.
        import run_queue
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sb = _fixture(tmp)  # storyboard_ch01 + glossary + approval
            review = root / 'review' / 'ch01'
            review.mkdir(parents=True)
            (review / 'storyboard.md').write_text('storyboard view')
            (review / 'timeline.md').write_text('timeline view')
            (review / 'manifest.json').write_text(json.dumps({
                'chapter': '01', 'date': '2026-11-04', 'blocks': 3,
                'storyboard_sha': C.sha256(sb),
                'glossary_sha': C.sha256(root / 'glossary_ch01.json'),
                'confirmed_terms': ['siva'], 'approved': False,
                'storyboard_view_sha': C.sha256(review / 'storyboard.md'),
                'timeline_sha': C.sha256(review / 'timeline.md'), 'sheet_sha': '0' * 64,
                'publisher_sha': C.sha256(ROOT / 'core' / 'builders' / 'publish_review.py'),
                'timeline_builder_sha': C.sha256(ROOT / 'core' / 'builders' / 'holds_timeline.py')}))
            finals = root / 'finals'
            finals.mkdir()
            reg = {'tantrasara': {'01': {}}, 'processes': {}, 'locks': {}, 'queue': []}
            with mock.patch.object(run_queue, 'BASE', root), \
                 mock.patch.object(run_queue, 'FINALS_DIR', finals):
                run_queue.refresh(reg)
                self.assertEqual(reg['tantrasara']['01']['stage'], 'approved-ready')
                issues_dir = finals.parent / 'issues'
                issues_dir.mkdir()
                (issues_dir / 'ch01.issues.json').write_text(json.dumps({
                    'version': 1, 'unit': '01', 'storyboard_sha256': C.sha256(sb),
                    'issues': [{'id': 'machine-deva-1', 'kind': 'machine-deva',
                                'severity': 'needs-owner', 'detail': 'test blocker',
                                'blocks': [], 'skill': 'machine-deva',
                                'status': 'open', 'resolution_note': ''}]}))
                reg['tantrasara']['01'] = {}
                run_queue.refresh(reg)
                self.assertEqual(reg['tantrasara']['01']['stage'], 'approved-ready')


class TestMcpServerNameLock(unittest.TestCase):
    def test_no_root_mcp_server_shadow(self):
        # propose_draws imports sleepdraw's `mcp_server` module by bare name.
        # A root-level videofactory/mcp_server.py shadows it on sys.path
        # (python -m puts cwd first): _seals() then returns OUR module and
        # bank tests die on .presets() AttributeError instead of the
        # designed RuntimeError-unavailable path. The factory MCP server
        # must never claim that name (ours: vf_mcp_server.py).
        self.assertFalse((ROOT / 'mcp_server.py').exists(),
                         'root mcp_server.py shadows sleepdraw mcp_server import')
        self.assertTrue((ROOT / 'vf_mcp_server.py').exists())

    def test_seals_unavailable_is_runtime_error(self):
        # With sleepdraw absent, bank reuse still works; fresh drafting
        # raises RuntimeError (caught by propose), never AttributeError.
        import propose_draws as P
        try:
            seals = P._seals()
        except RuntimeError:
            return
        self.assertTrue(callable(getattr(seals, 'presets', None)),
                        '_seals() returned a module without presets()')


if __name__ == '__main__':
    unittest.main()
