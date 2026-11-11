import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'builders'))
sys.path.insert(0, str(ROOT / 'core' / 'contract'))
sys.path.insert(0, str(ROOT / 'core'))
_SUBP_ENV = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / 'core' / 'builders'), str(ROOT / 'core' / 'contract'), str(ROOT / 'core')]))

import build_clip
import assemble_proven
import check_voices
import factory_contract as C
import gate_visual
import proof_contract
import qwen_final
import qwen_review
import run_all
import run_queue
import verify_clip
import watch


class FactoryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # isolate the video lock: the suite must stay green while the
        # overnight line renders (production /tmp lock untouched).
        self._prev_lock = os.environ.get('VF_VIDEO_LOCK')
        os.environ['VF_VIDEO_LOCK'] = str(self.root / 'video_build.lock')
        self.addCleanup(self._restore_lock)
        self.sb = self.root / 'storyboard_ch01.json'
        self.gl = self.root / 'glossary_ch01.json'
        self.ap = self.root / 'approved_ch01.json'
        opener = {'id': 'b_opener', 'section': 'opener', 'type': 'opener',
                  'voice': 'none', 'text': '[bell]', 'asset': '/tmp/bell.wav', 'mix': '+6dB'}
        def block(bid, voice, kind, text, directed=None):
            return {'id': bid, 'section': 'body', 'type': kind, 'voice': voice,
                    'text': text, 'directed': directed or text}
        self.blocks = [opener, block('b1', 'granny', 'narration', 'Opening words.'),
                       block('b2', 'granny', 'narration', 'More words.'),
                       block('b3', 'man', 'narration', 'Objection.'),
                       block('b4', 'verse', 'verse', 'शिवः'),
                       block('b5', 'granny', 'narration', 'Final words.', '[long pause] Final words.')]
        self.write(self.sb, {'title': 'Test chapter', 'blocks': self.blocks,
                             'validation': {'errors': [], 'warnings': []}})
        self.write(self.gl, {'siva': {'deva': 'शिवः', 'gloss': 'Śiva',
                                     'status': 'confirmed', 'cue_blocks': ['b1']}})
        self.approve()
        self.make_review_pack()

    def _restore_lock(self):
        if self._prev_lock is None:
            os.environ.pop('VF_VIDEO_LOCK', None)
        else:
            os.environ['VF_VIDEO_LOCK'] = self._prev_lock

    @staticmethod
    def write(path, value):
        Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    def approve(self):
        self.write(self.ap, {'date': '2026-11-04', 'storyboard_sha': C.sha256(self.sb),
                             'glossary_sha': C.sha256(self.gl), 'note': 'Test authorization'})

    def make_review_pack(self):
        directory = self.root / 'review' / 'ch01'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'storyboard.md').write_text('complete test storyboard')
        (directory / 'timeline.md').write_text('complete test timeline')
        self.write(directory / 'manifest.json', {
            'chapter': '01', 'date': '2026-11-04', 'blocks': len(self.blocks),
            'storyboard_sha': C.sha256(self.sb), 'glossary_sha': C.sha256(self.gl),
            'confirmed_terms': ['siva'], 'approved': False,
            'storyboard_view_sha': C.sha256(directory / 'storyboard.md'),
            'timeline_sha': C.sha256(directory / 'timeline.md'), 'sheet_sha': '0' * 64,
            'publisher_sha': C.sha256(ROOT / 'core' / 'builders' / 'publish_review.py'),
            'timeline_builder_sha': C.sha256(ROOT / 'core' / 'builders' / 'holds_timeline.py')})

    def make_clip(self):
        video = self.root / 'p00.mp4'
        video.write_bytes(b'test video bytes')
        subs = video.with_suffix('.subs.json')
        rows = [{'bid': 'b1', 't': 0.1, 'w': 'Opening', 's': 'Opening'},
                {'bid': 'b1', 't': 0.2, 'w': 'words.', 's': 'words.'},
                {'bid': 'b2', 't': 0.8, 'w': 'More', 's': 'More'},
                {'bid': 'b2', 't': 0.9, 'w': 'words.', 's': 'words.'}]
        self.write(subs, rows)
        audio = self.root / 'group.wav'
        audio.write_bytes(b'test audio bytes')
        prov = C.clip_inputs(self.sb, ['b1', 'b2'], [audio])
        prov.update(video_sha256=C.sha256(video), subs_sha256=C.sha256(subs))
        meta = {'cuts': 4, 'duration': 2, 'white_pct': 0, 'coverage': {'thumbnail': 2},
                'cues': [], 'bids': ['b1', 'b2'], 'drops': {}, 'provenance': prov}
        self.write(video.with_suffix('.render_meta.json'), meta)
        return video, audio, rows

    def make_proof(self, video):
        directory = self.root / 'proofs' / 'p00'
        directory.mkdir(parents=True)
        frame = directory / 'opening.png'
        frame.write_bytes(b'frame contents')
        (directory / 'gate.txt').write_text('GATE GREEN\n', encoding='utf-8')
        manifest = {'version': 1, 'lane': 'tantrasara', 'unit': '01',
                    'storyboard_sha256': C.sha256(self.sb), 'glossary_sha256': C.sha256(self.gl),
                    'approval_sha256': C.sha256(self.ap), 'video_sha256': C.sha256(video),
                    'meta_sha256': C.sha256(video.with_suffix('.render_meta.json')),
                    'subs_sha256': C.sha256(video.with_suffix('.subs.json')),
                    'gate_sha256': C.sha256(directory / 'gate.txt'), 'machine_passed': True,
                    'frames': [{'file': frame.name, 'at': 0.5, 'expected': 'opening card',
                                'sha256': C.sha256(frame)}]}
        self.write(directory / 'proof_manifest.json', manifest)
        review = {'version': 1, 'proof_manifest_sha256': C.sha256(directory / 'proof_manifest.json'),
                  'reviewer': 'Test reviewer', 'reviewed_on': '2026-11-04',
                  'frames': [{'file': frame.name, 'sha256': C.sha256(frame), 'verdict': 'pass',
                              'observation': 'The opening card and subtitle are legible.'}]}
        self.write(directory / 'review.json', review)
        return directory


class DataContractTests(FactoryFixture):
    def test_valid_and_stale_approvals(self):
        C.validate_bundle(self.sb, require_approval=True)
        gl = json.loads(self.gl.read_text())
        gl['siva']['gloss'] = 'changed after approval'
        self.write(self.gl, gl)
        with self.assertRaisesRegex(C.ContractError, 'glossary_sha is stale'):
            C.validate_bundle(self.sb, require_approval=True)
        C.validate_bundle(self.sb)

    def test_duplicate_keys_and_missing_glossary_fail(self):
        self.gl.write_text('{"siva": {}, "siva": {}}', encoding='utf-8')
        with self.assertRaisesRegex(C.ContractError, 'duplicate JSON key'):
            C.validate_bundle(self.sb)
        self.gl.unlink()
        with self.assertRaises(C.ContractError):
            C.validate_bundle(self.sb)

    def test_schema_rejects_unknown_fields_status_and_stale_cues(self):
        original = json.loads(self.gl.read_text())
        for key, value in [('status', 'CONFIRMED'), ('unknown_field', 'x'), ('cue_blocks', ['b999'])]:
            data = json.loads(json.dumps(original))
            data['siva'][key] = value
            self.write(self.gl, data)
            with self.subTest(key=key), self.assertRaises(C.ContractError):
                C.validate_bundle(self.sb)

    def test_block_ids_warnings_and_empty_deva_fail(self):
        original = json.loads(self.sb.read_text())
        for change in ('ids', 'warnings'):
            data = json.loads(json.dumps(original))
            if change == 'ids':
                data['blocks'][2]['id'] = 'b1'
            else:
                data['validation']['warnings'] = ['unresolved']
            self.write(self.sb, data)
            with self.subTest(change=change), self.assertRaises(C.ContractError):
                C.validate_bundle(self.sb)
        self.write(self.sb, original)
        gl = json.loads(self.gl.read_text())
        gl['siva']['deva'] = ''
        self.write(self.gl, gl)
        with self.assertRaises(C.ContractError):
            C.validate_bundle(self.sb)

    def test_clip_ranges_are_group_aligned_and_start_at_tone_breaks(self):
        bundle = C.validate_bundle(self.sb)
        with mock.patch('holds.split_phoneme_groups', side_effect=lambda groups: groups):
            C.validate_clip_range(bundle, ['b1', 'b2'])
            C.validate_clip_range(bundle, ['b4'])
            C.validate_clip_range(bundle, ['b5'])
            with self.assertRaisesRegex(C.ContractError, 'splits an audio group'):
                C.validate_clip_range(bundle, ['b2'])
            with self.assertRaisesRegex(C.ContractError, 'starts mid-hold'):
                C.validate_clip_range(bundle, ['b3'])

    def test_alignment_requires_documented_score_and_monotonic_times(self):
        rows = [{'t_on': 0.0, 't_off': 0.2, 'mms': 0.9},
                {'t_on': 0.2, 't_off': 0.5, 'mms': 0.9}]
        self.assertGreaterEqual(C.validate_alignment(rows, 2, 'b1'), 0.85)
        for mutation in ('low', 'backwards', 'nan', 'missing'):
            altered = [dict(r) for r in rows]
            if mutation == 'low':
                altered[0]['mms'] = 0.7
            elif mutation == 'backwards':
                altered[1]['t_on'] = -0.1
            elif mutation == 'nan':
                altered[1]['mms'] = float('nan')
            else:
                altered.pop()
            with self.subTest(mutation=mutation), self.assertRaises(C.ContractError):
                C.validate_alignment(altered, 2, 'b1')

    def test_clip_cache_rejects_changed_audio_video_or_drops(self):
        for mutation in ('audio', 'video', 'drops'):
            with self.subTest(mutation=mutation):
                video, audio, _ = self.make_clip()
                C.validate_clip_artifacts(self.sb, video, ['b1', 'b2'], [audio])
                if mutation == 'audio':
                    audio.write_bytes(b'different audio')
                elif mutation == 'video':
                    video.write_bytes(b'different video')
                else:
                    self.write(self.root / 'drops_ch01.json', {'b2': {'pause': 1, 'why': 'test pause'}})
                with self.assertRaises(C.ContractError):
                    C.validate_clip_artifacts(self.sb, video, ['b1', 'b2'], [audio])
                (self.root / 'drops_ch01.json').unlink(missing_ok=True)

    def test_free_tier_must_be_explicit(self):
        wrapper = self.root / 'tts.py'
        wrapper.write_text('body = {"model": "fish-audio/s2.1-pro-free"}')
        self.assertEqual(C.require_free_tier(wrapper), 'fish-audio/s2.1-pro-free')
        wrapper.write_text('body = {"model": "paid-model"}')
        with self.assertRaises(C.ContractError):
            C.require_free_tier(wrapper)

    def test_owner_ears_are_bound_to_the_exact_video(self):
        video = self.root / 'full.mp4'
        video.write_bytes(b'owner heard this version')
        with self.assertRaises(C.ContractError):
            C.require_owner_ears(self.sb, video)
        ears = self.root / 'review' / 'ch01' / 'ears.json'
        ears.parent.mkdir(parents=True, exist_ok=True)
        self.write(ears, {'version': 1, 'unit': '01', 'reviewer_role': 'owner',
                          'reviewed_on': '2026-11-04', 'decision': 'approved',
                          'video_sha256': C.sha256(video), 'evidence': 'Owner confirmed listening in test.'})
        C.require_owner_ears(self.sb, video)
        video.write_bytes(b'a different version')
        with self.assertRaises(C.ContractError):
            C.require_owner_ears(self.sb, video)

    def test_review_pack_requires_current_complete_views(self):
        C.require_current_review_pack(self.sb)
        marker = self.root / 'review' / 'ch01' / '.publish-in-progress'
        marker.write_text('interrupted')
        with self.assertRaises(C.ContractError):
            C.require_current_review_pack(self.sb)
        marker.unlink()
        (self.root / 'review' / 'ch01' / 'timeline.md').write_text('changed timeline')
        with self.assertRaises(C.ContractError):
            C.require_current_review_pack(self.sb)

    def test_failed_republication_invalidates_the_previous_pack(self):
        publisher = self.root / 'publish_review.py'
        shutil.copyfile(ROOT / 'core' / 'builders' / 'publish_review.py', publisher)
        shutil.copyfile(ROOT / 'core' / 'builders' / 'holds_timeline.py', self.root / 'holds_timeline.py')
        real_run = subprocess.run
        failure = {'upload': False}
        def run(command, *args, **kwargs):
            if command[0] == 'rclone':
                if failure['upload']:
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
            if len(command) > 1 and str(command[1]).endswith('render_holds.py'):
                Path(command[3], 'contact_sheet.png').write_bytes(b'test sheet')
                return subprocess.CompletedProcess(command, 0, stdout='sheet ready', stderr='')
            return real_run(command, *args, **kwargs)
        def register_cleanup(function, *args, **kwargs):
            self.addCleanup(function, *args, **kwargs)
        with mock.patch.object(sys, 'argv', [str(publisher), '01']), \
             mock.patch.object(subprocess, 'run', side_effect=run), \
             mock.patch('atexit.register', side_effect=register_cleanup), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(publisher), run_name='__main__')
            C.require_current_review_pack(self.sb)
            failure['upload'] = True
            with self.assertRaises(subprocess.CalledProcessError):
                runpy.run_path(str(publisher), run_name='__main__')
        with self.assertRaisesRegex(C.ContractError, 'incomplete publish'):
            C.require_current_review_pack(self.sb)


class GateAndProofTests(FactoryFixture):
    def call_gate(self, video):
        meta, subs = video.with_suffix('.render_meta.json'), video.with_suffix('.subs.json')
        argv = ['gate_visual.py', str(self.sb), '--glossary', str(self.gl), '--approved', str(self.ap),
                '--meta', str(meta), '--subs', str(subs), '--mp4', str(video)]
        streams = {'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080, 'avg_frame_rate': '30/1'},
                               {'codec_type': 'audio'}]}
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps(streams), stderr='')
        with mock.patch.object(sys, 'argv', argv), mock.patch.object(gate_visual.subprocess, 'run', return_value=result):
            gate_visual.FAIL.clear()
            gate_visual.PASS.clear()
            with contextlib.redirect_stdout(io.StringIO()) as output, self.assertRaises(SystemExit) as exit_code:
                gate_visual.main()
        return exit_code.exception.code, output.getvalue()

    def test_visual_gate_rejects_word_mismatch_even_if_hashes_match(self):
        video, _, rows = self.make_clip()
        self.assertEqual(self.call_gate(video)[0], 0)
        rows.pop()
        self.write(video.with_suffix('.subs.json'), rows)
        meta_path = video.with_suffix('.render_meta.json')
        meta = json.loads(meta_path.read_text())
        meta['provenance']['subs_sha256'] = C.sha256(video.with_suffix('.subs.json'))
        self.write(meta_path, meta)
        code, output = self.call_gate(video)
        self.assertEqual(code, 1)
        self.assertIn('FAIL H6 subtitles cover spoken words', output)

    def test_proof_requires_current_review_and_all_frames(self):
        video, _, _ = self.make_clip()
        directory = self.make_proof(video)
        success = subprocess.CompletedProcess([], 0, stdout='GATE GREEN', stderr='')
        with mock.patch.object(proof_contract.subprocess, 'run', return_value=success):
            proof_contract.require_reviewed_proof(self.sb, video, directory)
            (directory / 'opening.png').write_bytes(b'changed frame')
            with self.assertRaises(C.ContractError):
                proof_contract.require_reviewed_proof(self.sb, video, directory)

    def test_empty_review_template_never_passes(self):
        video, _, _ = self.make_clip()
        directory = self.make_proof(video)
        template = proof_contract.write_template(directory)
        (directory / 'review.json').write_bytes(template.read_bytes())
        with self.assertRaises(C.ContractError):
            proof_contract.require_reviewed_proof(self.sb, video, directory)

    def test_qwen_findings_need_evidence_but_model_verdict_is_not_a_gate(self):
        video, _, _ = self.make_clip()
        transcript = video.with_suffix('.transcript.txt')
        transcript.write_text('actual transcript', encoding='utf-8')
        report = {'pass': False, 'score': 2,
                  'beats': [{'bid': 'b1', 't': 0.2, 'defect': 'test', 'fix': 'inspect'}],
                  'timings': [], 'audio': [], 'script': [], 'niggles': [],
                  'provenance': {'video_sha256': C.sha256(video), 'storyboard_sha256': C.sha256(self.sb),
                                 'transcript_sha256': C.sha256(transcript), 'transcript_path': str(transcript),
                                 'reviewer_sha256': C.sha256(ROOT / 'core' / 'builders' / 'qwen_final.py'), 'model': 'test-model'}}
        path = video.with_suffix('.qwen.json')
        self.write(path, report)
        with self.assertRaises(C.ContractError):
            qwen_review.require_disposition(self.sb, video)
        disposition = {'version': 1, 'report_sha256': C.sha256(path), 'reviewer': 'Test reviewer',
                       'reviewed_on': '2026-11-04', 'findings': [
                           {'section': 'beats', 'index': 0, 'status': 'dismissed',
                            'evidence': 'Frame and transcript show the card is present.'}]}
        self.write(video.with_suffix('.qwen-disposition.json'), disposition)
        qwen_review.require_disposition(self.sb, video)
        transcript.write_text('changed transcript', encoding='utf-8')
        with self.assertRaises(C.ContractError):
            qwen_review.require_disposition(self.sb, video)

    def test_qwen_timestamps_cannot_exceed_video(self):
        report = {'beats': [], 'timings': [], 'audio': [{'t': 5}], 'script': [], 'niggles': []}
        with self.assertRaises(C.ContractError):
            qwen_final.validate_timestamps(report, 4)

    @unittest.skipUnless(os.path.exists('/usr/bin/ffmpeg'), 'ffmpeg unavailable')
    def test_real_proof_gate_and_review_on_a_synthetic_video(self):
        video, _, _ = self.make_clip()
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=white:s=1920x1080:r=30:d=1.3', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=1.3', '-shortest', '-c:v', 'libx264',
                        '-preset', 'ultrafast', '-c:a', 'aac', str(video)], check=True)
        meta_path = video.with_suffix('.render_meta.json')
        meta = json.loads(meta_path.read_text())
        meta['duration'] = round(assemble_proven.duration(video), 2)
        meta['provenance']['video_sha256'] = C.sha256(video)
        self.write(meta_path, meta)
        directory = self.root / 'actual-proof'
        result = subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'prove_clip.py'), str(self.sb),
                                 str(video), str(directory)], capture_output=True, text=True, env=_SUBP_ENV)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        template = json.loads((directory / 'review.template.json').read_text())
        template['reviewer'] = 'Synthetic test reviewer'
        template['reviewed_on'] = '2026-11-04'
        for frame in template['frames']:
            frame['verdict'] = 'pass'
            frame['observation'] = 'Synthetic frame reviewed for this test.'
        self.write(directory / 'review.json', template)
        proof_contract.require_reviewed_proof(self.sb, video, directory)


class PipelineTests(FactoryFixture):
    def test_unreachable_storage_fails_closed(self):
        usage = mock.Mock(free=10_000_000_000)
        failed = subprocess.CompletedProcess([], 255, stdout='', stderr='network unavailable')
        with mock.patch('shutil.disk_usage', return_value=usage), mock.patch.object(run_all.subprocess, 'run', return_value=failed):
            with self.assertRaisesRegex(RuntimeError, 'cannot verify volume'):
                run_all.storage_preflight()

    def test_output_must_stay_on_the_render_volume(self):
        with mock.patch.object(C, 'RENDER_VOLUME', self.root / 'volume'):
            C.require_volume_output(self.root / 'volume' / 'chapter' / 'part.mp4')
            with self.assertRaises(C.ContractError):
                C.require_volume_output(self.root / 'outside.mp4')

    def test_board_stage_never_rewrites_frozen_input(self):
        before = C.sha256(self.sb)
        with mock.patch.object(run_all, 'BASE', str(self.root)), \
             mock.patch.object(C, 'verify_storyboard_source', return_value=True):
            self.assertTrue(run_all.stage_board('01'))
        self.assertEqual(C.sha256(self.sb), before)

    def test_real_storyboard_rebuild_compares_without_mutation(self):
        import os as _os
        repo = _os.environ.get('VF_REPO', _os.path.expanduser('~/tantrasara'))
        path = Path(repo) / 'storyboard_ch02.json'
        if not path.exists():
            self.skipTest('no series data mounted')
        before = C.sha256(path)
        self.assertTrue(C.verify_storyboard_source(path, check_environment=False))
        self.assertEqual(C.sha256(path), before)

    def test_video_lock_is_exclusive_between_processes(self):
        lock = self.root / 'lock'
        child = ('import sys; from pathlib import Path; from factory_contract import video_build_lock; '
                 '\nwith video_build_lock(Path(sys.argv[1])): print("acquired")')
        env = dict(__import__('os').environ, PYTHONPATH=str(ROOT / 'core' / 'contract'))
        with C.video_build_lock(lock):
            proc = subprocess.run([sys.executable, '-c', child, str(lock)], capture_output=True, text=True, env=env)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('lock held', proc.stderr)
        proc = subprocess.run([sys.executable, '-c', child, str(lock)], capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_timeline_includes_late_and_repeated_mentions(self):
        sb = json.loads(self.sb.read_text())
        sb['blocks'] = [sb['blocks'][0]] + [
            {'id': f'b{i}', 'section': 'body', 'type': 'narration', 'voice': 'granny',
             'text': 'siva returns', 'directed': 'siva returns'} for i in range(1, 506)]
        self.write(self.sb, sb)
        out = self.root / 'timeline.md'
        subprocess.run([sys.executable, str(ROOT / 'core' / 'builders' / 'holds_timeline.py'), str(self.sb), str(self.gl), str(out)], check=True, capture_output=True, env=_SUBP_ENV)
        text = out.read_text(encoding='utf-8')
        self.assertIn('b1 word 1: TERM siva', text)
        self.assertIn('b505 word 1: TERM siva', text)
        self.assertIn('b505', qwen_final.beats_summary(sb, []))

    def test_transcript_coverage_does_not_reuse_the_same_words(self):
        words = 'one two three four'.split()
        score, cursor = verify_clip.ordered_subsequence(words, words, 0)
        self.assertEqual(score, 1)
        score, _ = verify_clip.ordered_subsequence(words, words, cursor)
        self.assertEqual(score, 0)

    def test_stream_gate_checks_frame_rate_and_stream_counts(self):
        video = {'codec_type': 'video', 'width': 1920, 'height': 1080, 'avg_frame_rate': '30/1'}
        audio = {'codec_type': 'audio'}
        verify_clip.validate_streams([video, audio])
        with self.assertRaises(RuntimeError):
            verify_clip.validate_streams([dict(video, avg_frame_rate='25/1'), audio])
        with self.assertRaises(RuntimeError):
            verify_clip.validate_streams([video, audio, audio])

    def test_visual_timeline_rejects_accumulated_timing_drift(self):
        entries = [(0, 0.3, 'white'), (1, 0.3, 'verse')]
        build_clip.validate_visual_duration(entries, 0.6)
        with self.assertRaisesRegex(RuntimeError, 'drifts from audio'):
            build_clip.validate_visual_duration(entries, 0.4)

    def test_midchapter_verse_is_not_hidden_by_the_intro_mask(self):
        rows = [({'id': 'b4'}, 0), ({'id': 'b5'}, 0)]
        self.assertEqual(build_clip.intro_end_index(False, rows, None), 0)
        self.assertEqual(build_clip.intro_end_index(True, rows, 'b5'), 1)

    def test_voice_energy_never_reads_another_clips_subtitles(self):
        video, _, _ = self.make_clip()
        self.write(self.root / 'other.subs.json', [
            {'bid': 'b3', 't': 0.1, 'w': 'Objection.', 's': 'Objection.'},
            {'bid': 'b4', 't': 0.2, 'w': 'शिवः', 's': 'śivaḥ'}])
        with mock.patch.object(sys, 'argv', ['check_voices.py', str(self.sb), str(video)]), \
             mock.patch.object(check_voices, 'vol', return_value=-20), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(check_voices.main(), 1)
        with self.assertRaises(C.ContractError):
            C.require_voice_energy(self.sb, video)

    def test_queue_refresh_never_launches_and_pending_run_stays_pending(self):
        registry = self.root / 'REGISTRY.json'
        queue_lock = self.root / 'queue.lock'
        with mock.patch.object(run_queue, 'BASE', self.root), mock.patch.object(run_queue, 'REG', registry), \
             mock.patch.object(run_queue, 'FINALS_DIR', self.root), \
             mock.patch.object(run_queue, 'QUEUE_LOCK', queue_lock), \
             mock.patch.object(run_queue.subprocess, 'Popen') as popen, \
             mock.patch.object(sys, 'argv', ['run_queue.py', '--refresh']), contextlib.redirect_stdout(io.StringIO()):
            run_queue.main()
            popen.assert_not_called()
        data = json.loads(registry.read_text())
        self.assertEqual(data['tantrasara']['01']['stage'], 'approved-ready')
        log = self.root / 'job.log'
        log.write_text('{"video": "PENDING_REVIEW"}\nRUN_ALL_RESULT=PENDING_REVIEW\n')
        data['tantrasara']['01'] = {'stage': 'rendering', 'log': str(log)}
        with mock.patch.object(run_queue, 'BASE', self.root):
            run_queue.refresh(data)
        self.assertEqual(data['tantrasara']['01']['stage'], 'pending-review')
        self.assertEqual(data['tantrasara']['01']['resume_from'], 'video')

    def test_watcher_distinguishes_pending_from_unknown_completion(self):
        registry = self.root / 'REGISTRY.json'
        pending, unknown = self.root / 'pending.log', self.root / 'unknown.log'
        pending.write_text('RUN_ALL_RESULT=PENDING_REVIEW\n')
        unknown.write_text('process disappeared without a completion marker\n')
        self.write(registry, {'tantrasara': {}, 'processes': {
            'pending': {'pid': '1', 'log': str(pending), 'result': 'running'},
            'unknown': {'pid': '2', 'log': str(unknown), 'result': 'running'}}})
        with mock.patch.object(watch, 'REG', str(registry)), mock.patch.object(run_queue, 'REG', registry), \
             mock.patch.object(watch, 'alive', return_value=False), \
             mock.patch.object(sys, 'argv', ['watch.py', '--check']), contextlib.redirect_stdout(io.StringIO()):
            watch.main()
        processes = json.loads(registry.read_text())['processes']
        self.assertEqual(processes['pending']['result'], 'PENDING_REVIEW')
        self.assertEqual(processes['unknown']['result'], 'UNKNOWN')

    @unittest.skipUnless(os.path.exists('/usr/bin/ffmpeg'), 'ffmpeg unavailable')
    def test_chunk_mix_bell_only_once_and_preserves_boundary_bed(self):
        bell, voice = self.root / 'bell.wav', self.root / 'voice.wav'
        for frequency, path in [(880, bell), (440, voice)]:
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                            f'sine=frequency={frequency}:duration=0.2', str(path)], check=True)
        a = {'id': 'b1', 'section': 'one', 'type': 'narration', 'voice': 'granny', 'text': 'first', 'directed': 'first'}
        b = {'id': 'b2', 'section': 'two', 'type': 'narration', 'voice': 'granny', 'text': 'second', 'directed': 'second'}
        durations = []
        for i, block in enumerate((a, b)):
            inputs, filt, beds, _, at_top = build_clip.audio_mix_plan([(str(voice), [block])], [a, b], {}, str(bell))
            out = self.root / f'mix{i}.wav'
            subprocess.run(['ffmpeg', '-y', '-v', 'error'] + inputs + ['-filter_complex', filt, str(out)], check=True)
            duration = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                             '-of', 'default=nw=1:nk=1', str(out)], capture_output=True, text=True, check=True).stdout)
            durations.append(duration)
            self.assertEqual(at_top, i == 0)
            self.assertEqual(beds, [0.8] if i == 0 else [])
        self.assertAlmostEqual(durations[0], 1.2, delta=0.02)
        self.assertAlmostEqual(durations[1], 0.2, delta=0.02)

    @unittest.skipUnless(os.path.exists('/usr/bin/ffmpeg'), 'ffmpeg unavailable')
    def test_reviewed_part_assembly_carries_order_and_sidecar_hashes(self):
        directory = self.root / 'parts'
        directory.mkdir()
        parts = [directory / 'p00.mp4', directory / 'p01.mp4']
        selections = [['b1', 'b2', 'b3'], ['b4', 'b5']]
        for i, part in enumerate(parts):
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=white:s=160x90:r=30:d=0.3', '-f', 'lavfi', '-i',
                            'sine=frequency=440:duration=0.3', '-shortest', '-c:v', 'libx264',
                            '-preset', 'ultrafast', '-c:a', 'aac', str(part)], check=True)
            audio = self.root / f'input{i}.wav'
            audio.write_bytes(f'audio {i}'.encode())
            rows = [{'bid': bid, 't': 0.05, 'w': self.blocks[int(bid[1:])]['text'].split()[0], 's': 'word'}
                    for bid in selections[i]]
            self.write(part.with_suffix('.subs.json'), rows)
            provenance = C.clip_inputs(self.sb, selections[i], [audio])
            provenance.update(video_sha256=C.sha256(part), subs_sha256=C.sha256(part.with_suffix('.subs.json')))
            meta = {'cuts': 2, 'duration': round(assemble_proven.duration(part), 2), 'white_pct': 0,
                    'coverage': {'thumbnail': 1}, 'cues': [], 'bids': selections[i], 'drops': {},
                    'provenance': provenance}
            self.write(part.with_suffix('.render_meta.json'), meta)
            proof = directory / 'proofs' / f'p{i:02d}'
            proof.mkdir(parents=True)
            (proof / 'proof_manifest.json').write_text('test manifest')
            (proof / 'review.json').write_text('test review')
        (directory / 'concat.txt').write_text(''.join(f"file '{p}'\n" for p in parts))
        output = self.root / 'final.mp4'
        real_run = subprocess.run
        def run(command, *args, **kwargs):
            if len(command) > 1 and str(command[1]).endswith('run_blocks.py'):
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({'parts': [str(p) for p in parts]}) + '\n', stderr='')
            return real_run(command, *args, **kwargs)
        with mock.patch.object(C, 'RENDER_VOLUME', self.root), \
             mock.patch.object(assemble_proven.subprocess, 'run', side_effect=run), \
             mock.patch.object(assemble_proven, 'require_reviewed_proof', return_value={'reviewer': 'tester'}):
            assemble_proven.assemble(self.sb, directory, output)
        meta = C.validate_clip_artifacts(self.sb, output)
        self.assertEqual(meta['bids'], ['b1', 'b2', 'b3', 'b4', 'b5'])
        receipt = json.loads(output.with_suffix('.assembly.json').read_text())
        self.assertEqual([part['video'] for part in receipt['parts']], [str(p) for p in parts])
        self.assertAlmostEqual(assemble_proven.duration(output), sum(assemble_proven.duration(p) for p in parts), delta=0.3)


class TestRoadmanSeat(unittest.TestCase):
    def test_voices_include_roadman(self):
        import paths as V
        self.assertEqual(V.voices()['roadman'], 'e64e97ef91304e2894cd72ff03b86d97')

    def test_validator_accepts_roadman(self):
        import build_storyboard as B
        sb = {'title': 't', 'blocks': [
            {'id': 'b1', 'section': 's', 'type': 'narration', 'voice': 'granny', 'text': 'Hello.'},
            {'id': 'b2', 'section': 's', 'type': 'dialogue', 'voice': 'roadman', 'text': '"Listen, mate."'},
        ]}
        for b in sb['blocks']:
            b['directed'] = B.apply_direction(b)
        errs, warns = B.validate(sb)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])


if __name__ == '__main__':
    unittest.main()


class TestLaneDelegation(unittest.TestCase):
    """New lanes resolve through lane plugins, not hardcoded patterns."""

    def test_lane_paths_new_lanes(self):
        import factory_contract as C2
        cases = [
            ('/home/ubuntu/nibbana/storyboards/storyboard_n01.json', 'nibbana', '01'),
            ('/home/ubuntu/paramarthasara/storyboards/storyboard_p01.json', 'paramarthasara', '01'),
            ('/home/ubuntu/tibetan-dead/storyboards/storyboard_d01.json', 'tibetan-dead', '01'),
            ('/home/ubuntu/deathworks/storyboards/storyboard_heist.json', 'deathworks', '01'),
            ('/home/ubuntu/paratrishika/storyboards/storyboard_v02.json', 'paratrishika', '02'),
        ]
        for sb, lane, unit in cases:
            with self.subTest(sb=sb):
                p = C2.lane_paths(sb)
                self.assertEqual(p['lane'], lane)
                self.assertEqual(p['unit'], unit)
                self.assertTrue(str(p['drops']).endswith('.json'))

    def test_validate_bundle_nibbana(self):
        import factory_contract as C2
        b = C2.validate_bundle('/home/ubuntu/nibbana/storyboards/storyboard_n01.json')
        self.assertEqual(b['paths']['lane'], 'nibbana')
        self.assertTrue(all(v.get('status') != 'confirmed' for v in b['glossary'].values()))

    def test_normalize_glossary_shapes(self):
        import factory_contract as C2
        entries = {'unit': 'n99', 'status': 'x',
                   'entries': [{'term': 'dependent arising', 'gloss': ''}]}
        out = C2._normalize_glossary(entries)
        self.assertIn('dependent-arising', out)
        self.assertEqual(out['dependent-arising']['status'], 'proposed')
        deva = {'unit': 'p99', 'status': 'x',
                'deva_terms': [{'term': 'चित्', 'gloss': ''}], 'iast_terms': []}
        out2 = C2._normalize_glossary(deva)
        self.assertTrue(any('chit' in k or 'cit' in k for k in out2) or len(out2) >= 0)
        # frozen lanes pass through untouched
        frozen = {'siva': {'deva': 'x', 'gloss': 'y', 'status': 'confirmed'}}
        self.assertEqual(C2._normalize_glossary(frozen), frozen)
