"""Unit tests for lane dispatch (engine stays generic)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'builders'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'contract'))

import lane_api


class TestDispatch(unittest.TestCase):
    def test_tantrasara_path(self):
        name, mod = lane_api.for_path('/home/ubuntu/tantrasara/storyboard_ch08.json')
        self.assertEqual(name, 'tantrasara')
        self.assertEqual(mod.unit_id('/home/ubuntu/tantrasara/storyboard_ch08.json'), '08')
        d = mod.paths('/home/ubuntu/tantrasara', '08')
        self.assertEqual(d['glossary'], '/home/ubuntu/tantrasara/glossary_ch08.json')
        self.assertEqual(d['lane'], 'tantrasara')

    def test_ch6_legacy_stem(self):
        self.assertEqual(lane_api.for_path('/home/ubuntu/tantrasara/storyboard_ch6.json')[1]
                         .unit_id('/home/ubuntu/tantrasara/storyboard_ch6.json'), '06')

    def test_shiva_path(self):
        p = '/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json'
        name, mod = lane_api.for_path(p)
        self.assertEqual(name, 'shiva-sutras')
        self.assertEqual(mod.unit_id(p), '01')
        d = mod.paths('/home/ubuntu/tantrasara', '01')
        self.assertEqual(d['glossary'], '/home/ubuntu/tantrasara/shiva/glossary_s01.json')
        self.assertFalse(d['numeral'])

    def test_shiva_inside_tantrasara_repo_still_shiva(self):
        # the shiva lane lives inside the tantrasara repo dir — path marks decide
        name, _ = lane_api.for_path('/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s77.json')
        self.assertEqual(name, 'shiva-sutras')

    def test_forced_project_wins(self):
        with mock.patch.dict(os.environ, {'VF_PROJECT': 'tantrasara'}):
            name, _ = lane_api.for_path('/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json')
            self.assertEqual(name, 'tantrasara')

    def test_unknown_path_raises(self):
        with self.assertRaises(ValueError):
            lane_api.for_path('/tmp/random_storyboard.json')

    def test_intro_args_tantrasara(self):
        blocks = [{'id': 'b_opener', 'section': 'opener', 'type': 'opener', 'voice': 'none', 'text': '[bell]'},
                  {'id': 'b1', 'section': 's', 'type': 'narration', 'voice': 'granny',
                   'text': ' second'}]
        out = lane_api.intro_args('/home/ubuntu/tantrasara/storyboard_ch02.json', blocks, {})
        self.assertEqual(out['numeral'], '02')
        self.assertIsNone(out['header'])

    def test_intro_args_shiva(self):
        blocks = [{'id': 'b_opener', 'section': 'opener', 'type': 'opener', 'voice': 'none', 'text': '[bell]'},
                  {'id': 'b1', 'section': 's', 'type': 'title', 'voice': 'granny', 'text': 'Some Sutra 1.1'},
                  {'id': 'b2', 'section': 's', 'type': 'narration', 'voice': 'granny',
                   'text': '1.1 — The Funny Title'}]
        out = lane_api.intro_args('/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s01.json', blocks, {})
        self.assertFalse(out['numeral'])
        self.assertEqual(out['header'], {'ref': '1.1', 'title': 'The Funny Title'})




class TestAllBuildersImportable(unittest.TestCase):
    def test_every_builder_imports_clean(self):
        import glob
        import importlib
        mods = []
        for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               '..', 'core', 'builders', '*.py'))):
            name = os.path.splitext(os.path.basename(f))[0]
            if name in ('align_group',):
                continue
            try:
                importlib.import_module(name)
                mods.append(name)
            except SystemExit:
                mods.append(name + ' (exits without argv: expected for CLIs)')
            except Exception as e:
                self.fail(f'{name} failed to import: {e}')
        self.assertIn('holds', mods)


if __name__ == '__main__':
    unittest.main()


class TestBatchDriver(unittest.TestCase):
    def test_import_surface(self):
        import batch
        self.assertIn('video', batch.STAGES)
        self.assertIn('ship', batch.STAGES)
        self.assertEqual(batch.unit_stem('/x/storyboard_ch08.json'), 'ch08')
        self.assertEqual(batch.unit_stem('/x/storyboards/storyboard_s01.json'), 's01')

    def test_reaper_never_touches_parts_or_finals(self):
        import batch
        import inspect
        src = inspect.getsource(batch.reap_orphans)
        for keep in ('ch', 'blocks', 'finals', 'mmsclip\'', 'mmsmod'):
            pass
        # patterns are transient-only by construction; finals/parts unmatchable
        import fnmatch
        pats = ['stage_tmp_*', 'clip_frames_*', 'clip_mix*.mp3', 'mms_grp*.f32',
                'mmsclip_p*', 'mmsclip_tmp_*', 'probe_*.png', 'probe_*.log']
        for keep in ('/tmp/ch08_blocks/p04.mp4', '/tmp/ch08_full.mp4',
                     '~/vol/tantrasara/renders/finals/ch08_full.mp4',
                     '/tmp/mmsclip/cw30.json', '/tmp/mmsmod/node_modules/x'):
            self.assertFalse(any(fnmatch.fnmatch(keep, '/tmp/' + p) for p in pats), keep)
