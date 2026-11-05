"""Unit tests for lane dispatch (engine stays generic)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

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


if __name__ == '__main__':
    unittest.main()
