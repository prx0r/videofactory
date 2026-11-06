"""Ship-gate tests: independent validator, success criteria, anti-cheat.

The validator (validate_ship.py) must catch what the estimator misses and
must never share the estimator's code path: it reads ONLY measured
artifacts (part render_metas, verify sidecars), never storyboard estimates,
never scan_holds / gate_storyboard / build_clip.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))
sys.path.insert(0, str(ROOT / 'core'))

import factory_contract as C


def _h(s='x'):
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()


def _meta(entries, duration=None):
    total = sum(e['dur'] for e in entries)
    cov = {}
    for e in entries:
        cov[e['kind']] = cov.get(e['kind'], 0) + e['dur']
    return {'cuts': len(entries), 'duration': duration if duration is not None else round(total, 2),
            'white_pct': round(100 * cov.get('white', 0) / (total or 1)),
            'coverage': {k: round(v) for k, v in cov.items()},
            'entries': [{'dur': e['dur'], 'kind': e['kind']} for e in entries],
            'cues': [], 'bids': ['b1'], 'drops': {},
            'clips': [{'key': 'k', 't_start': 0.0, 't_complete': 1.0, 'clear': 'cut',
                        'fade': 1.5, 'why': 'test draw', 'asset_sha': 'ab12cd34ef56ab78', 'muted': True}],
            'provenance': {'inputs': {'version': 1, 'lane': 'tantrasara', 'unit': '01',
                                      'bids': ['b1'], 'storyboard': _h('sb'), 'glossary': _h('gl'),
                                      'approval': _h('ap'), 'drops': None, 'static': {},
                                      'audio': [{'path': 'g.wav', 'sha256': _h('au')}]},
                           'inputs_sha256': _h('in'), 'video_sha256': _h('v'), 'subs_sha256': _h('s')}}


class ShipValidatorTests(unittest.TestCase):
    def test_gates_registry_lists_green(self):
        r = subprocess.run([sys.executable, str(ROOT / 'core' / 'contract' / 'gates_registry.py'), '--list'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('GATES GREEN', r.stdout)
        self.assertIn('ship/max-white-span-v1', r.stdout)

    def test_success_criteria_versioned(self):
        import success as S
        self.assertEqual(S.SHIP_CRITERIA_VERSION, 'tantrasara-ship-v1')
        self.assertEqual(S.MAX_WHITE_SPAN_S, 60.0)
        self.assertTrue(any(c[0] == 'ship/max-white-span-v1' for c in S.CRITERIA))

    def test_render_meta_entries_roundtrip_schema(self):
        m = _meta([{'dur': 1.0, 'kind': 'white'}, {'dur': 2.0, 'kind': 'term:x'}])
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'p00.render_meta.json')
            json.dump(m, open(p, 'w'))
            C.validate_schema('render-meta', json.load(open(p)), p)

    def _run_criterion(self, parts):
        import validate_ship as V
        with tempfile.TemporaryDirectory() as tmp:
            for i, entries in enumerate(parts):
                json.dump(_meta(entries), open(os.path.join(tmp, f'p{i:02d}.render_meta.json'), 'w'))
            ok, ev = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'ch01_full.mp4'),
                                                parts_dir=tmp)
            return ok, ev

    def test_max_white_span_pass_and_fail(self):
        ok, ev = self._run_criterion([[{'dur': 30.0, 'kind': 'white'}, {'dur': 5.0, 'kind': 'term:x'}]])
        self.assertTrue(ok)
        self.assertLessEqual(ev['max_white_span_s'], 60.0)
        ok, ev = self._run_criterion([[{'dur': 61.0, 'kind': 'white'}]])
        self.assertFalse(ok)
        self.assertIn('61', ev['reason'])

    def test_boundary_merge_and_unknown(self):
        # trailing 40s white + leading 30s white across the seam = 70s single hold
        ok, ev = self._run_criterion([[{'dur': 5.0, 'kind': 'term:x'}, {'dur': 40.0, 'kind': 'white'}],
                                      [{'dur': 30.0, 'kind': 'white'}, {'dur': 5.0, 'kind': 'verse'}]])
        self.assertFalse(ok)
        self.assertEqual(ev['boundary_merged_s'], 70.0)
        import validate_ship as V
        with tempfile.TemporaryDirectory() as tmp:
            ok, ev = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'ch01_full.mp4'), parts_dir=tmp)
            self.assertIsNone(ok)  # no part metas: UNKNOWN, never ships

    def test_entries_integrity_blocks_tampering(self):
        import validate_ship as V
        with tempfile.TemporaryDirectory() as tmp:
            m = _meta([{'dur': 10.0, 'kind': 'white'}])
            m['cuts'] = 99  # lie about cuts
            json.dump(m, open(os.path.join(tmp, 'p00.render_meta.json'), 'w'))
            ok, ev = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'ch01_full.mp4'), parts_dir=tmp)
            self.assertFalse(ok)
            m2 = _meta([{'dur': 10.0, 'kind': 'white'}], duration=999.0)  # drifted duration
            json.dump(m2, open(os.path.join(tmp, 'p01.render_meta.json'), 'w'))
            os.remove(os.path.join(tmp, 'p00.render_meta.json'))
            ok, ev = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'ch01_full.mp4'), parts_dir=tmp)
            self.assertFalse(ok)

    def test_validator_deterministic(self):
        import validate_ship as V
        with tempfile.TemporaryDirectory() as tmp:
            json.dump(_meta([{'dur': 59.0, 'kind': 'white'}]),
                      open(os.path.join(tmp, 'p00.render_meta.json'), 'w'))
            r1 = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'x_full.mp4'), parts_dir=tmp)
            r2 = V.criterion_max_white_span('sb.json', os.path.join(tmp, 'x_full.mp4'), parts_dir=tmp)
            self.assertEqual(str(r1), str(r2))
            self.assertTrue(r1[0])

    def test_antidote_no_missed_holdable_sanskrit(self):
        import subprocess
        for sb in ('/home/ubuntu/tantrasara/storyboard_ch15.json',
                   '/home/ubuntu/tantrasara/storyboard_ch02.json'):
            r = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'audit_white_gaps.py'), sb],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('BUG (confirmed term spoken, no cue): 0', r.stdout)
            self.assertIn('ANTIDOTE GREEN', r.stdout)

    def test_validator_independent_of_estimator(self):
        # independence = no code dependency on the estimator path (imports
        # only); docstring mentions are fine and intentional.
        src = Path(ROOT, 'core', 'builders', 'validate_ship.py').read_text()
        imports = [ln.strip() for ln in src.splitlines()
                   if ln.strip().startswith(('import ', 'from '))]
        blob = '\n'.join(imports)
        for forbidden in ('scan_holds', 'gate_storyboard', 'holds_timeline', 'run_blocks', 'build_clip',
                          'import holds', 'from holds'):
            self.assertNotIn(forbidden, blob)


if __name__ == '__main__':
    unittest.main()
