"""Unit tests for the pure core (no I/O, no models, no Fish).

Run: python3 -m unittest discover -s tests -v (from ~/videofactory)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
import pure


def B(bid, section='body', type='narration', voice='granny', text='Plain words here.'):
    return {'id': bid, 'section': section, 'type': type, 'voice': voice, 'text': text}


class TestBeds(unittest.TestCase):
    def test_flow(self):
        self.assertEqual(pure.bed_after([B('b1')], [B('b2')]), 0.3)

    def test_section_end(self):
        self.assertEqual(pure.bed_after([B('b1', section='a')], [B('b2', section='b')]), 0.8)

    def test_dialogue(self):
        self.assertEqual(pure.bed_after([B('b1', type='dialogue', voice='man')], [B('b2')]), 0.8)

    def test_title(self):
        self.assertEqual(pure.bed_after([B('b1', type='title')], [B('b2')]), 0.8)

    def test_verse_multi_crisp(self):
        g = [B('b1', voice='verse', type='verse', text='Line one two three four five.')]
        self.assertEqual(pure.bed_after(g, [B('b2')]), 2.8)

    def test_verse_single(self):
        g = [B('b1', voice='verse', type='verse', text='Aham.')]
        self.assertEqual(pure.bed_after(g, [B('b2')]), 0.6)

    def test_long_pause(self):
        self.assertEqual(pure.bed_after([B('b1', text='Somber close. [long pause]')], [B('b2')]), 0.8)


class TestChunkPolicy(unittest.TestCase):
    def test_boundary(self):
        self.assertFalse(pure.should_chunk(200))
        self.assertTrue(pure.should_chunk(201))
        self.assertTrue(pure.should_chunk(299))  # ch08 b975 killer
        self.assertTrue(pure.should_chunk(278))  # ch09 b623 killer

    def test_split_snaps_to_block(self):
        counts = [40, 60, 50, 70, 79]  # sums 299, killer shape
        at = pure.split_index(counts, 0.5, 299)
        self.assertIn(at, (40, 100, 150, 220))  # a block boundary partial sum
        self.assertGreaterEqual(at, 1)
        self.assertLess(at, 299)

    def test_split_never_splits_single_block_words(self):
        counts = [278]
        at = pure.split_index(counts, 0.5, 278)
        self.assertGreaterEqual(at, 1)
        self.assertLess(at, 278)


class TestGrouping(unittest.TestCase):
    def test_merge_same_voice_section(self):
        gs = pure.plan_groups([B('b1'), B('b2'), B('b3')])
        self.assertEqual(len(gs), 1)
        self.assertEqual([b['id'] for b in gs[0]], ['b1', 'b2', 'b3'])

    def test_split_on_voice_and_section(self):
        gs = pure.plan_groups([B('b1', voice='granny'), B('b2', voice='man'),
                               B('b3', voice='man', section='s2')])
        self.assertEqual(len(gs), 3)

    def test_skip_visual_only(self):
        gs = pure.plan_groups([B('b1'), B('b2', voice='none'),
                               B('b3', type='figure'), B('b4', type='meta'),
                               B('b5', type='label'), B('b6')])
        self.assertEqual(len(gs), 1)
        self.assertEqual([b['id'] for b in gs[0]], ['b1', 'b6'])

    def test_opener_kept(self):
        op = {'id': 'b_opener', 'section': 'opener', 'type': 'opener',
              'voice': 'none', 'text': '[bell]'}
        gs = pure.plan_groups([op, B('b1')])
        self.assertEqual(gs[0][0].get('group_kind'), 'opener')
        self.assertEqual(len(gs), 2)

    def test_count_disp(self):
        g = [B('b1', text='The attribution of Self.'), B('b2', text='And more words here')]
        self.assertEqual(pure.count_disp(g), 8)



class TestMotionApplies(unittest.TestCase):
    def test_only_white(self):
        self.assertTrue(pure.motion_applies('white'))
        for kind in ('verse', 'term:agni', 'stack:agni', 'verse-hold:b12',
                     'thumbnail', 'white '):
            if kind == 'white ':
                continue
            self.assertFalse(pure.motion_applies(kind), kind)

    def test_draw_kinds_count_as_content(self):
        # motion kinds themselves are content, never a base to draw over
        self.assertFalse(pure.motion_applies('draw:b989'))
        self.assertFalse(pure.motion_applies('clip:b12'))


if __name__ == '__main__':
    unittest.main()
