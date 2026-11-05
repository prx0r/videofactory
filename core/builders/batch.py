#!/usr/bin/env python3
"""Lane-generic overnight batch driver (the fleet pattern as code).

Usage: python3 batch.py --project tantrasara --units 08,09 [--from STAGE] [--dry-run] [--ship]

One unit at a time (video lock holds across units); one failure never
blocks the next. Every stage logs to its own file; progress derives from
logs, never memory. All subprocess calls time-bounded (BARS: timeouts
everywhere). Opens with an orphan reaper (BARS 26) and storage preflight.
Ship to R2 is opt-in (--ship); default is volume-only.

Stages mirror the proven overnight flow: audio-check -> parts -> prove ->
concat -> verify (record-only) -> voices (gates) -> volume finals.
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import paths as _vf

STAGES = ['audio', 'video', 'prove', 'concat', 'verify', 'voices', 'ship']
LONG_TIMEOUT = 10800   # 3h: full audio renders / chunk video builds
SHORT_TIMEOUT = 600    # 10m: probes, concats, checks, uploads


def log(msg, logf):
    line = f'{time.strftime("%FT%TZ", time.gmtime())} {msg}'
    print(line, flush=True)
    logf.write(line + '\n')
    logf.flush()


def sh(cmd, timeout, logf, tail=500):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        logf.write(f'TIMEOUT {timeout}s: {" ".join(cmd)}\n{(e.stderr or "")[-tail:]}\n')
        logf.flush()
        return False, f'timeout-{timeout}s'
    logf.write((r.stderr or r.stdout or '')[-3000:] + f'\nRC={r.returncode}\n')
    logf.flush()
    return r.returncode == 0, (r.stderr or r.stdout or '')[-tail:]


def reap_orphans(logf, dry=False):
    """Sweep leaked transients from crashed runs (all reproducible; parts,
    finals, and model deps untouched). Skipped on dry-run, and skipped
    while another video build holds the lock (never sweep a live build)."""
    import glob
    if dry:
        log('orphan reaper: skipped (dry-run)', logf)
        return
    try:
        holder = open('/tmp/video_build.lock').read().strip()
        try:
            os.kill(int(holder), 0)
            log(f'orphan reaper: skipped (video lock held by live pid {holder})', logf)
            return
        except (OSError, ValueError):
            pass
    except OSError:
        pass
    pats = ['stage_tmp_*', 'clip_frames_*', 'clip_mix*.mp3', 'mms_grp*.f32',
            'mmsclip_p*', 'mmsclip_tmp_*', 'probe_*.png', 'probe_*.log']
    n = 0
    for pat in pats:
        for p in glob.glob(os.path.join('/tmp', pat)):
            try:
                (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
                n += 1
            except OSError:
                pass
    log(f'orphan reaper: swept {n}', logf)


def unit_stem(sb_path):
    base = os.path.basename(sb_path)
    if base.startswith('storyboard_'):
        base = base[len('storyboard_'):]
    return os.path.splitext(base)[0]


def run_unit(sb_path, frm, dry, ship, logf):
    import lane_api as _api
    name, mod = _api.for_path(sb_path)
    unit = mod.unit_id(sb_path)
    stem = unit_stem(sb_path)
    renders = _vf.renders_root()
    outdir = f'/tmp/{stem}_blocks'
    vol_final = os.path.join(renders, 'finals', f'{stem}_full.mp4')
    tmp_full = f'/tmp/{stem}_full.mp4'
    B = os.path.dirname(os.path.abspath(__file__))

    if dry:
        for s in STAGES[STAGES.index(frm):]:
            log(f'{stem} stage {s}: DRY-RUN (no-op)', logf)
        return True, 'dry'

    def stage(name, cmd, timeout):
        if STAGES.index(name) < STAGES.index(frm):
            return True, 'skipped'
        log(f'{stem} stage {name}', logf)
        if dry:
            log(f'{stem} stage {name}: DRY-RUN (no-op)', logf)
            return True, 'dry'
        return sh(cmd, timeout, logf)

    ok, _ = stage('audio', [sys.executable, f'{B}/render_chapter.py', sb_path], LONG_TIMEOUT)
    if not ok:
        return False, 'audio'
    ok, _ = stage('video', [sys.executable, f'{B}/run_blocks.py', sb_path, outdir, '600'], LONG_TIMEOUT)
    if not ok:
        return False, 'video'
    import glob as _g
    for part in sorted(_g.glob(f'{outdir}/p*.mp4')):
        ok, _ = stage('prove', [sys.executable, f'{B}/prove_clip.py', sb_path, part,
                                f'/tmp/{stem}_proof_{os.path.basename(part)}'], SHORT_TIMEOUT)
        if not ok:
            return False, f'prove-{part}'
    ok, _ = stage('concat', ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0',
                             '-i', f'{outdir}/concat.txt', '-c', 'copy', tmp_full], SHORT_TIMEOUT)
    if not ok:
        return False, 'concat'
    ok, _ = stage('verify', [sys.executable, f'{B}/verify_clip.py', sb_path, tmp_full], SHORT_TIMEOUT)
    log(f'{stem} verify {"PASS" if ok else "FAIL-whisper-only"} (record only, never gates)', logf)
    ok, _ = stage('voices', [sys.executable, f'{B}/check_voices.py', sb_path, tmp_full], SHORT_TIMEOUT)
    if not ok:
        return False, 'voices'
    os.makedirs(os.path.dirname(vol_final), exist_ok=True)
    shutil.copy(tmp_full, vol_final)
    try:
        shutil.copy(tmp_full + '.verify.json', vol_final + '.verify.json')
    except OSError:
        pass
    if ship:
        ok, _ = stage('ship', ['timeout', '300', 'rclone', 'copyto', tmp_full,
                               f'{_vf.r2_prefix()}/{stem}_full.mp4'], SHORT_TIMEOUT)
        if ok:
            r = subprocess.run(['rclone', 'lsl', f'{_vf.r2_prefix()}/{stem}_full.mp4'],
                               capture_output=True, text=True, timeout=120)
            try:
                remote = int(r.stdout.strip().split()[0])
                ok = (remote == os.path.getsize(tmp_full))
            except (IndexError, ValueError):
                ok = False
        if not ok:
            return False, 'ship-verify'
    subprocess.run(['rm', '-rf', outdir, tmp_full, tmp_full + '.verify.json'])
    for d in _g.glob(f'/tmp/{stem}_proof*'):
        subprocess.run(['rm', '-rf', d])
    return True, 'shipped' if ship else 'volume-only'


def main():
    args = sys.argv[1:]
    if '--help' in args or '-h' in args:
        sys.exit(__doc__)
    if '--project' in args:
        _vf.apply_series(args[args.index('--project') + 1])
    units = []
    if '--units' in args:
        units = args[args.index('--units') + 1].split(',')
    if '--storyboards' in args:
        units += args[args.index('--storyboards') + 1].split(',')
    if not units:
        sys.exit('batch.py: --units 08,09 (lane unit ids) or --storyboards PATH,...')
    frm = args[args.index('--from') + 1] if '--from' in args else STAGES[0]
    dry = '--dry-run' in args
    ship = '--ship' in args
    logf = open('/tmp/batch.log', 'a', buffering=1)
    reap_orphans(logf, dry)
    import lane_api as _api
    failed = []
    for u in units:
        sb = u if os.path.exists(u) else None
        if sb is None:
            # resolve unit id through the active project lane
            import glob as _g
            cands = []
            for proj in sorted(os.listdir(_api.projects_dir())):
                if proj.startswith('_'):
                    continue
                try:
                    mod = _api.load_lane(proj)
                    repo = _vf.repo_root()
                    if not hasattr(mod, 'paths'):
                        continue
                    import re as _re2
                    _digits = _re2.sub(r'\D', '', u).zfill(2)
                    for _uu in dict.fromkeys([u, _digits]):
                        cands += mod.paths(repo, _uu).get('storyboards', [])
                except ValueError:
                    pass
                except Exception:
                    pass
            sb = next((c for c in cands if os.path.exists(c)), None)
        if sb is None:
            log(f'{u}: storyboard not found in any lane', logf)
            failed.append(u)
            continue
        ok, where = run_unit(sb, frm, dry, ship, logf)
        log(f'{u} {"done" if ok else "FAIL@" + where}', logf)
        if not ok:
            failed.append(u)
    log(f'BATCH-DONE failed={failed or "none"}', logf)


if __name__ == '__main__':
    main()
