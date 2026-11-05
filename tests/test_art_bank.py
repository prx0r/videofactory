#!/usr/bin/env python3
"""Art-bank + gap-proposer tests (synthetic fixtures only, no paid calls)."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'builders'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
import propose_draws as P  # noqa: E402

BANK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'art_bank', 'REGISTRY.json')


class BankTests(unittest.TestCase):
    def test_registry_is_honest(self):
        reg = json.load(open(BANK, encoding='utf-8'))
        self.assertEqual(reg['format'], 'trika-art-bank/1')
        kinds = {e['id']: e for e in reg['entries']}
        self.assertIn('spider-song04', kinds)
        for e in reg['entries']:
            anchored = (e.get('verse_anchors') not in (None, '', 'unassigned')
                        and e.get('essence_anchors') not in (None, '', 'unassigned'))
            self.assertTrue(anchored or e['status'] in ('PROPOSED', 'MACHINE_DRAFT'),
                            e['id'])
            if e.get('asset'):
                self.assertTrue(e.get('recipe'), e['id'])

    def test_bank_lookup_hits_mala_spider_sea(self):
        hit, _ = P.bank_lookup('the ceremony of the sacred garland')
        self.assertEqual(hit['id'], 'queue-mala')
        hit, _ = P.bank_lookup('she spun herself into knots like a spider')
        self.assertEqual(hit['id'], 'spider-song04')
        hit, _ = P.bank_lookup('the still sea that spilled the sky')
        self.assertEqual((hit or {}).get('id'), 'p1-15')

    def test_proposer_marks_bank_and_never_draws_name(self):
        sb = {'blocks': [
            {'id': 'b1', 'type': 'narration', 'voice': 'granny', 'section': 'S',
             'text': 'Right.', 'directed': 'Right.'},
            {'id': 'b2', 'type': 'narration', 'voice': 'granny', 'section': 'S',
             'text': 'The garland holds fifty names.', 'directed': 'The garland holds fifty names.'},
        ]}
        tl = 'b2: WHITE (tone break)\n'
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, 'storyboard_ch99.json')
            tp = os.path.join(d, 'timeline.md')
            op = os.path.join(d, 'draws_ch99.proposed.json')
            json.dump(sb, open(sp, 'w'))
            open(tp, 'w').write(tl)
            path, props = P.propose(sp, tp, op)
            self.assertEqual(path, op)
            self.assertIn('b2', props)
            self.assertEqual(props['b2']['bank']['bank_id'], 'queue-mala')
            self.assertIsNone(props['b2']['asset'])
            saved = json.load(open(op))
            self.assertEqual(saved['meta']['priority'], 'normal')
            self.assertEqual(saved['meta']['lane'], 'tantrasara')

    def test_white_map_marks_priority_and_never_bids(self):
        sb = {'blocks': [
            {'id': 'b1', 'type': 'narration', 'voice': 'granny', 'section': 'S',
             'text': 'Right.', 'directed': 'Right.'},
            {'id': 'b2', 'type': 'narration', 'voice': 'granny', 'section': 'S',
             'text': 'Still here.', 'directed': 'Still here.'},
        ]}
        tl = 'b2: WHITE (tone break)\n'
        wm = '| 99 | 10.0m | 50% | 212s@250, 30s@9 |\n'
        with tempfile.TemporaryDirectory() as d:
            sp = os.path.join(d, 'storyboard_ch99.json')
            tp = os.path.join(d, 'timeline.md')
            wp = os.path.join(d, 'white-map.md')
            op = os.path.join(d, 'out.proposed.json')
            json.dump(sb, open(sp, 'w'))
            open(tp, 'w').write(tl)
            open(wp, 'w').write(wm)
            path, props = P.propose(sp, tp, op, white_map_md=wp)
            saved = json.load(open(path))
            self.assertEqual(saved['meta']['priority'], 'high')
            self.assertEqual(saved['meta']['white_map_stuck'][0]['seconds'], 212)
            # stuck refs are estimator marks, never block ids
            self.assertNotIn('b250', props)

    def test_proposed_file_can_never_render(self):
        import holds as H
        fake_lane_drops = '/tmp/vf_test_lane_drops_ch99.json'
        with unittest.mock.patch.object(H, 'lane_for',
                                        return_value={'drops': fake_lane_drops}):
            got = H.draws_for('/tmp/vf_test_lane_storyboard_ch99.json')
            self.assertEqual(got, {})


if __name__ == '__main__':
    unittest.main()
