#!/usr/bin/env python3
"""Lane-generic overnight batch driver (the fleet pattern as code).

Usage: python3 batch.py --project tantrasara --units 08,09 [--from STAGE] [--dry-run] [--ship]

One unit at a time (video lock holds across units); one failure never
blocks the next. Every stage logs to its own file; progress derives from
logs, never memory. All subprocess calls time-bounded (BARS: timeouts
everywhere). Opens with an orphan reaper (BARS 26) and storage preflight.
Ship to R2 is opt-in (--ship); default is volume-only.

Stages mirror the proven overnight flow: issues (record-only work list
with skill pointers) -> audio-check -> parts -> prove -> concat ->
verify (record-only) -> validate-ship (record-only verdict) ->
voices (gates) -> volume finals.
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

STAGES = ['issues', 'audio', 'video', 'prove', 'concat', 'verify', 'validate', 'voices', 'ship']
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
    # chunk parts live on the lane volume (never local disk — series law);
    # the output-on-volume gate rightly refuses /tmp production output,
    # and volume parts double as crash-resume cache (run_blocks CACHED).
    outdir = os.path.join(renders, f'{stem}_blocks')
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

    # issues first (record-only, never gates — downstream entries enforce):
    # the checker finds, the skill list tells how, the log is the work list.
    _issues_dir = os.path.join(renders, 'issues')
    os.makedirs(_issues_dir, exist_ok=True)
    _issues_path = os.path.join(_issues_dir, f'{stem}.issues.json')
    ok, out = stage('issues', [sys.executable, f'{B}/check_issues.py', sb_path,
                               '--out', _issues_path], SHORT_TIMEOUT)
    try:
        _doc = json.load(open(_issues_path, encoding='utf-8'))
        _open = [i for i in _doc.get('issues', []) if i.get('status') == 'open']
        log(f'{stem} issues {"GREEN" if not _open else f"RED {len(_open)} open (skills attached in {_issues_path})"} (record only, never gates)', logf)
    except (OSError, ValueError):
        log(f'{stem} issues checker {"ok" if ok else "FAILED"} (no readable artifact)', logf)
    ok, _ = stage('audio', [sys.executable, f'{B}/render_chapter.py', sb_path], LONG_TIMEOUT)
    if not ok:
        return False, 'audio'
    ok, _ = stage('video', [sys.executable, f'{B}/run_blocks.py', sb_path, outdir, '600'], LONG_TIMEOUT)
    if not ok:
        return False, 'video'
    import glob as _g
    for part in sorted(_g.glob(f'{outdir}/p*.mp4')):
        # prove is RECORD-ONLY (owner order 2026-11-06: storyboard green is
        # the only render gate; no downstream check may hold a unit back).
        # Real breakage still surfaces: build_clip crashes fail the video
        # stage, concat fails loudly, R2 byte-match is enforced. Prove
        # verdicts are written beside the part for the record.
        ok, _ = stage('prove', [sys.executable, f'{B}/prove_clip.py', sb_path, part,
                                f'/tmp/{stem}_proof_{os.path.basename(part)}'], SHORT_TIMEOUT)
        if not ok:
            log(f'{stem} prove {os.path.basename(part)} recorded RED (non-blocking)', logf)
    ok, _ = stage('concat', ['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0',
                             '-i', f'{outdir}/concat.txt', '-c', 'copy', tmp_full], SHORT_TIMEOUT)
    if not ok:
        return False, 'concat'
    # parts-proof: per-part render_metas (measured hold entries the
    # independent ship validator reads) are copied beside finals BEFORE the
    # transient sweep — evidence survives the run that produced it.
    _proofdir = os.path.join(os.path.dirname(vol_final), f'{stem}_parts')
    os.makedirs(_proofdir, exist_ok=True)
    for _pm in sorted(_g.glob(f'{outdir}/p*.render_meta.json')) + [f'{outdir}/concat.txt']:
        try:
            if os.path.exists(_pm):
                shutil.copy(_pm, os.path.join(_proofdir, os.path.basename(_pm)))
        except OSError:
            pass
    ok, _ = stage('verify', [sys.executable, f'{B}/verify_clip.py', sb_path, tmp_full], SHORT_TIMEOUT)
    log(f'{stem} verify {"PASS" if ok else "FAIL-whisper-only"} (record only, never gates)', logf)
    # independent ship verdict (record-only, never gates — ears come later):
    # measured-artifacts check against tantrasara-ship-v1, verdict beside
    # the mp4 so the seal step never re-derives it.
    ok, _ = stage('validate', [sys.executable, f'{B}/validate_ship.py', sb_path, tmp_full,
                               '--parts-dir', _proofdir,
                               '--out', tmp_full + '.ship.json'], SHORT_TIMEOUT)
    log(f'{stem} validate-ship {"GREEN" if ok else "RED (see .ship.json; ears/review outstanding are normal pre-seal)"} (record only, never gates)', logf)
    # voices is record-only like verify (owner order: no meter may hold up
    # a ship; silent seats are an ears matter, and ears are not required
    # to render). The report ships beside the final either way.
    ok, _ = stage('voices', [sys.executable, f'{B}/check_voices.py', sb_path, tmp_full], SHORT_TIMEOUT)
    log(f'{stem} voices {"PASS" if ok else "FAIL-recorded (ships anyway; ears dispose)"} (record only, never gates)', logf)
    os.makedirs(os.path.dirname(vol_final), exist_ok=True)
    shutil.copy(tmp_full, vol_final)
    assert os.path.getsize(vol_final) == os.path.getsize(tmp_full), 'volume copy byte-mismatch — tmp kept for retry'
    try:
        shutil.copy(tmp_full + '.verify.json', vol_final + '.verify.json')
    except OSError:
        pass
    try:
        shutil.copy(tmp_full + '.ship.json', vol_final + '.ship.json')
    except OSError:
        pass
    try:
        shutil.copy(os.path.splitext(tmp_full)[0] + '.voices.json', vol_final + '.voices.json')
    except OSError:
        pass
    # white-hold surfacing (owner worry: long white / stuck cards).
    # Per-part render_metas already log COVERAGE; aggregate here so the
    # batch log names the worst offender before ears.
    try:
        import json as _js
        _whites, _worst = [], ('', 0)
        for _part in sorted(_g.glob(f'{outdir}/p*.mp4')):
            _mp = _part + '.render_meta.json'
            try:
                _m = _js.load(open(_mp))
                _cov = _m.get('coverage', {})
                _w = _cov.get('white', 0)
                _whites.append((_part, round(_w, 1), _m.get('white_pct', 0)))
                for _k, _v in _cov.items():
                    if isinstance(_v, (int, float)) and _v > _worst[1] and _k != 'white':
                        _worst = (_k, round(_v, 1))
            except OSError:
                pass
        if _whites:
            log(f'{stem} white-holds per part: {"; ".join(f"{p.split("/")[-1]} white={w}s ({pct}%)" for p, w, pct in _whites)}; longest single hold {_worst[0]}={_worst[1]}s', logf)
            if any(pct > 50 for _, _, pct in _whites):
                log(f'{stem} WARNING white>50% on {[p.split("/")[-1] for p, _, pct in _whites if pct > 50]} — owner ears must confirm pacing before seal', logf)
    except Exception as _e:
        log(f'{stem} white-report skipped: {_e}', logf)
    if ship:
        # delivery confirmation with retries: a transient network flake must
        # never hold up a finished unit, but an unverified upload is never
        # reported as shipped either.
        ok = False
        for _try in range(1, 4):
            if _try > 1:
                log(f'{stem} ship retry {_try}/3', logf)
            _ok, _ = stage('ship', ['timeout', '300', 'rclone', 'copyto', tmp_full,
                                    f'{_vf.r2_prefix()}/{stem}_full.mp4'], SHORT_TIMEOUT)
            if not _ok:
                continue
            r = subprocess.run(['rclone', 'lsl', f'{_vf.r2_prefix()}/{stem}_full.mp4'],
                               capture_output=True, text=True, timeout=120)
            try:
                remote = int(r.stdout.strip().split()[0])
                ok = (remote == os.path.getsize(tmp_full))
            except (IndexError, ValueError):
                ok = False
            if ok:
                break
            log(f'{stem} ship byte-mismatch on attempt {_try}, retrying', logf)
        # ship the sha-bound verify alongside the video (old line shipped
        # review packs + sealed videos only; verify proves these bytes).
        if ok and os.path.exists(tmp_full + '.verify.json'):
            ok, _ = stage('ship-verify', ['timeout', '120', 'rclone', 'copyto', tmp_full + '.verify.json',
                                          f'{_vf.r2_prefix()}/{stem}_full.mp4.verify.json'], SHORT_TIMEOUT)
        if not ok:
            return False, 'ship-verify'
    # tmp clear only after confirmed success: volume byte-match (+ R2
    # byte-match when --ship). Freed space logged; audio cache on volume
    # and model deps untouched.
    import shutil as _sh
    _before = _sh.disk_usage('/tmp').free
    subprocess.run(['rm', '-rf', outdir, tmp_full, tmp_full + '.verify.json', tmp_full + '.ship.json',
                    os.path.splitext(tmp_full)[0] + '.voices.json'])
    for d in _g.glob(f'/tmp/{stem}_proof*'):
        subprocess.run(['rm', '-rf', d])
    for d in _g.glob(f'/tmp/stage_tmp_{stem}_blocks*') + _g.glob('/tmp/stage_tmp_ch*'):
        subprocess.run(['rm', '-rf', d])
    _after = _sh.disk_usage('/tmp').free
    log(f'{stem} tmp cleared after confirmed success: freed {(_after - _before) / 1e9:.2f}G (tmp now {_after / 1e9:.1f}G free)', logf)
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
    forced_proj = args[args.index('--project') + 1] if '--project' in args else None
    for u in units:
        sb = u if os.path.exists(u) else None
        if sb is None:
            # resolve unit id through the project lane (forced --project
            # wins; otherwise every lane is tried and the first hit stands)
            import glob as _g
            cands = []
            projs = [forced_proj] if forced_proj else sorted(os.listdir(_api.projects_dir()))
            for proj in projs:
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
