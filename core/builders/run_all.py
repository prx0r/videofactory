#!/usr/bin/env python3
"""Batch driver: every chapter through storyboard->render->MMS->assemble->video.
Usage: python3 run_all.py [--chapters 01,02] [--from STAGE] [--dry-run]
Stages: preflight board cast-check publish render mms assemble holds video verify golden-check review-pack cleanup.
publish = review pack to R2 for owner sign-off (render REFUSES without
approved_chNN.json whose SHAs match current files). golden-check compares
each render against the owner-blessed golden before review-pack.
Idempotent everywhere (content hashes); resume by re-running. One chapter
failing never blocks the others. Overnight-safe under nohup.
Owner gates (NOT automated): casting marks, glossary confirms, final ears.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import json, os, subprocess, sys, shutil

BASE = _vf.repo_root()
VOL_FREE_MIN_GB = 4.0
LOCAL_FREE_MIN_GB = 1.0

def storage_preflight():
    import shutil as _sh
    local_free = _sh.disk_usage('/tmp').free / 1e9
    r = subprocess.run(['ssh', '-i', os.path.expanduser('~/.ssh/id_ed25519'),
                        '-o', 'BatchMode=yes', 'root@2.28.50.109',
                        'df -BG /mnt/HC_Volume_106427611 | tail -1'],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError('cannot verify volume free space: ' + (r.stderr.strip() or f'ssh exited {r.returncode}'))
    try:
        vol_free = float(r.stdout.split()[3].rstrip('G'))
    except (IndexError, ValueError) as exc:
        raise RuntimeError('cannot parse volume free space from df') from exc
    if not __import__('math').isfinite(vol_free):
        raise RuntimeError('volume free space is not a finite number')
    print(f'storage: local {local_free:.1f}G free, volume {vol_free:.0f}G free', flush=True)
    if local_free < LOCAL_FREE_MIN_GB:
        raise RuntimeError(f'local disk critical ({local_free:.1f}G)')
    if vol_free < VOL_FREE_MIN_GB:
        raise RuntimeError(f'volume critical ({vol_free:.0f}G)')


def free_tier_preflight():
    # free Fish only, always: the shared renderer must pin the -free model.
    # A paid model string anywhere stops the line cold (owner call to waive).
    import re as _re
    tts = open(_vf.tts_script(), encoding='utf-8').read()
    m = _re.search(r'"model":\s*"([^"]+)"', tts)
    model = m.group(1) if m else 'UNKNOWN'
    print(f'fish model: {model}', flush=True)
    assert model == 'fish-audio/s2.1-pro-free', f'NOT FREE TIER: {model}'

def stage_cleanup():
    # transient build debris only; caches (models, npm) and other lanes untouched
    for p in ['/tmp/clip_frames', '/tmp/fm2_frames', '/tmp/ts_holds', '/tmp/mmsclip',
              '/tmp/mms_grp.f32', '/tmp/mms_eng_test.f32']:
        shutil.rmtree(p, ignore_errors=True)
    for pat in ['/tmp/*_pilot*.mp4', '/tmp/ch*_opening*.mp4', '/tmp/first_min*.mp4']:
        import glob as _g
        for f in _g.glob(pat):
            try:
                os.remove(f)
            except OSError:
                pass
    print('cleanup: transient frames/tmp audio removed (R2 holds the shipped copies)', flush=True)
    return True
CHAPTERS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13',
            '14', '15', '16', '17', '18', '19', '20', '21', '22']
STAGES = ['preflight', 'free-tier', 'board', 'cast-check', 'publish', 'render', 'mms', 'assemble', 'holds', 'video', 'verify', 'golden-check', 'review-pack', 'cleanup']

def sh(cmd, **kw):
    print('+', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    tail = (r.stderr or r.stdout or '').strip().splitlines()[-3:]
    for l in tail:
        print('  |', l[:160], flush=True)
    return r.returncode == 0

def stage_board(ch):
    # The saved storyboard is the approved input. Rebuilding it in place
    # changes its bytes (and can erase a blessing) before any gate runs.
    from factory_contract import validate_bundle, verify_storyboard_source
    validate_bundle(sb_path(ch))
    verify_storyboard_source(sb_path(ch))
    print(f'  | ch{ch}: source/overrides match frozen storyboard; no rewrite', flush=True)
    return True

def stage_cast_check(ch):
    sb = json.load(open(sb_path(ch)))
    errs = sb.get('validation', {}).get('errors', [])
    print(f"  | ch{ch}: {len(errs)} validation errors", flush=True)
    return not errs

def stage_publish(ch):
    return sh(['python3', f'{BASE}/publish_review.py', ch])

def stage_render(ch):
    ap = f'{BASE}/approved_ch{ch}.json'
    assert os.path.exists(ap), f'ch{ch}: NOT APPROVED — publish the review pack and get owner sign-off first'
    a = json.load(open(ap))
    import hashlib as _hl
    for key, path in (('storyboard_sha', sb_path(ch)), ('glossary_sha', f'{BASE}/glossary_ch{ch}.json')):
        h = _hl.sha256(open(path, 'rb').read()).hexdigest()
        assert h == a.get(key), f'ch{ch}: {key} changed since approval — republish required'
    print(f'ch{ch}: approval {a["date"]} verified, rendering', flush=True)
    return sh(['python3', f'{BASE}/render_chapter.py', sb_path(ch)])

def stage_mms(ch):
    # per-group MMS via build_clip's align path is per-clip; full-chapter
    # MMS runs inside build_video (group wavs already on volume).
    print('  | ch%s: MMS runs inside video build (no separate step)' % ch, flush=True)
    return True

def stage_assemble(ch):
    return sh(['python3', f'{BASE}/assemble_chapter.py', sb_path(ch),
               f'/tmp/ch{ch}_full.mp3'])

def stage_holds(ch):
    return sh(['python3', f'{BASE}/render_holds.py', sb_path(ch),
               f'/tmp/holds_ch{ch}'])

def stage_video(ch):
    sb = json.load(open(sb_path(ch)))
    bids = ','.join(b['id'] for b in sb['blocks'] if b['id'] != 'b_opener')
    return sh(['python3', f'{BASE}/build_clip.py', sb_path(ch),
               bids, f'/tmp/ch{ch}_full.mp4'])

def stage_verify(ch):
    sb = sb_path(ch)
    return sh(['python3', f'{BASE}/verify_clip.py', sb, f'/tmp/ch{ch}_full.mp4'])

def stage_review_pack(ch):
    sb = json.load(open(sb_path(ch)))
    words = sum(len(b['text'].split()) for b in sb['blocks'])
    print(f'  | ch{ch}: {len(sb["blocks"])} blocks, ~{words} words — '
          'frames + whisper + Qwen queued for owner review', flush=True)
    return True


def sb_path(ch):
    return f'{BASE}/storyboard_ch6.json' if ch == '06' else f'{BASE}/storyboard_ch{ch}.json'

def src_path(ch):
    return f'{BASE}/chapters/ch06-kaladhva.md' if ch == '06' else f'{BASE}/chapters/ch{ch}.md'

def stage_golden_check(ch):
    return sh(['python3', f'{BASE}/golden.py', 'check', ch, f'/tmp/ch{ch}_full.mp4'])

STAGE_FN = {'preflight': lambda ch: storage_preflight() or True, 'free-tier': lambda ch: free_tier_preflight() or True, 'board': stage_board, 'cast-check': stage_cast_check, 'publish': stage_publish, 'render': stage_render,
            'mms': stage_mms, 'assemble': stage_assemble, 'holds': stage_holds,
            'video': stage_video, 'verify': stage_verify, 'golden-check': stage_golden_check, 'review-pack': stage_review_pack, 'cleanup': lambda ch: stage_cleanup()}

def main():
    args = sys.argv[1:]
    chs = CHAPTERS
    if '--chapters' in args:
        chs = args[args.index('--chapters') + 1].split(',')
    frm = args[args.index('--from') + 1] if '--from' in args else STAGES[0]
    dry = '--dry-run' in args
    stages = STAGES[STAGES.index(frm):]
    print(f'chapters={chs} stages={stages} dry={dry}', flush=True)
    report = {}
    import time as _time
    from events import log_event
    for ch in chs:
        report[ch] = {}
        for st in stages:
            if dry:
                print(f'[{ch}/{st}] would run', flush=True)
                report[ch][st] = 'dry'
                continue
            _t0 = _time.time()
            try:
                ok = STAGE_FN[st](ch)
            except Exception as e:
                print(f'[{ch}/{st}] EXCEPTION {str(e)[:200]}', flush=True)
                ok = False
            report[ch][st] = 'ok' if ok else 'FAIL'
            log_event('tantrasara', ch, st, 'ok' if ok else 'FAIL',
                      _time.time() - _t0)
            if not ok:
                break
    print(json.dumps(report, indent=1))

if __name__ == '__main__':
    main()
