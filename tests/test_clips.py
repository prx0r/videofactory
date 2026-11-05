"""Unit tests for overlay clips (synthetic lavfi assets only)."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'builders'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'contract'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

from PIL import Image
import holds as H


def make_clip(path, dur=2):
    r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi',
                        '-i', f'testsrc=size=320x240:rate=15:duration={dur}',
                        '-c:v', 'libx264', '-preset', 'ultrafast', path],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]


class TestOverlayClips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = '/tmp/vf_test_src.mp4'
        make_clip(cls.clip)
        frame = Image.new('RGB', (H.CANVAS_W, H.CANVAS_H), (200, 30, 30))
        frame.save('/tmp/vf_test_frame.png')
        cls.frame = '/tmp/vf_test_frame.png'
        cls.base = Image.new('RGB', (1920, 1080), (255, 255, 255))

    def test_canvas_geometry_safe(self):
        self.assertEqual((H.CANVAS_X, H.CANVAS_Y), (320, 145))
        self.assertLessEqual(H.CANVAS_Y + H.CANVAS_H, H.SUB_Y)

    def test_paste_colors_canvas_only(self):
        im = H.overlay_paste(self.base, Image.open(self.frame).convert('RGB'), 1.0)
        px = im.load()
        self.assertEqual(px[960, 400][:2], (200, 30))
        self.assertEqual(px[100, 100], (255, 255, 255))
        self.assertEqual(px[960, 900], (255, 255, 255))

    def test_fade_to_white(self):
        im = H.overlay_paste(self.base, Image.open(self.frame).convert('RGB'), 0.0)
        px = im.load()
        self.assertEqual(px[960, 400], (255, 255, 255))

    def test_wrong_size_rejected(self):
        with self.assertRaises(AssertionError):
            H.overlay_paste(self.base, Image.new('RGB', (100, 100), (0, 0, 0)))

    def test_prerender_cmd_shape(self):
        outdir = '/tmp/vf_test_canvas'
        os.makedirs(outdir, exist_ok=True)
        r = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-stream_loop', '-1', '-i', self.clip,
                            '-vf', f'scale={H.CANVAS_W}:{H.CANVAS_H}:force_original_aspect_ratio=decrease,'
                                   f'pad={H.CANVAS_W}:{H.CANVAS_H}:(ow-iw)/2:(oh-ih)/2:white,fps=15',
                            '-t', '2.1', '-an', f'{outdir}/f%05d.png'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        import glob
        frames = sorted(glob.glob(f'{outdir}/f*.png'))
        self.assertGreater(len(frames), 20)
        check = Image.open(frames[0])
        self.assertEqual(check.size, (H.CANVAS_W, H.CANVAS_H))

    def test_clips_spec_validation(self):
        import tempfile
        from unittest import mock
        lane = tempfile.mkdtemp(prefix='vf_lane_')
        sb = os.path.join(lane, 'storyboard_ch01.json')
        spec_path = os.path.join(lane, 'clips_ch01.json')
        json.dump({'b2': {'asset': self.clip, 'complete_bid': 'b9',
                          'clear': 'fade', 'fade': 1.5, 'why': 'test'}},
                  open(spec_path, 'w'))
        try:
            with mock.patch.dict(os.environ, {'VF_REPO': lane}):
                d = H.clips_for(sb)
            self.assertIn('b2', d)
            json.dump({'b2': {'asset': self.clip, 'complete_bid': 'b9'}}, open(spec_path, 'w'))
            with mock.patch.dict(os.environ, {'VF_REPO': lane}):
                with self.assertRaises(AssertionError):
                    H.clips_for(sb)
            import factory_contract as C
            C.validate_schema('clips', {'b2': {'asset': 'x.mp4', 'complete_bid': 'b9',
                                              'why': 't'}}, 'minimal')
            with self.assertRaises(Exception):
                C.validate_schema('clips', {'b2': {'asset': 'x.mp4', 'complete_bid': 'b9',
                                                  'clear': 'wipe', 'why': 't'}}, 'wipe rejected')
        finally:
            import shutil
            shutil.rmtree(lane, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
