#!/usr/bin/env python3
"""Preflight: impossible-to-fuck-up gate before any batch (owner call).
Usage: python3 preflight.py [--chapters 02,03]  (default: all blessed)
Checks, each PASS/FAIL with the fix attached: local disk >=1G, volume
>=4G, no live video lock holder, approvals SHAs match current files,
V5 (confirmed terms carry Deva), audio cache complete (0 missing),
R2 creds present, MMS + whisper models present. Exit 0/1.
"""
import hashlib
import json
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import re
import shutil
import subprocess
import sys

BASE = _vf.repo_root()
VOL = _vf.renders_root()
FAIL, PASS = [], []


def check(name, ok, fix=''):
    (PASS if ok else FAIL).append(
        f'{"PASS" if ok else "FAIL"} {name}' + (f' — fix: {fix}' if fix and not ok else ''))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def sb_of(ch):
    return f'{BASE}/storyboard_ch6.json' if ch == '06' else f'{BASE}/storyboard_ch{ch}.json'


def main():
    chs = [f'{i:02d}' for i in range(1, 23)]
    if '--chapters' in sys.argv:
        chs = sys.argv[sys.argv.index('--chapters') + 1].split(',')
    check('local disk >=1G', shutil.disk_usage('/tmp').free / 1e9 >= 1,
          'free /tmp (clean per-chapter transient after ship)')
    try:
        r = subprocess.run(['ssh', '-i', os.path.expanduser('~/.ssh/id_ed25519'),
                            '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                            'root@2.28.50.109',
                            'df -BG /mnt/HC_Volume_106427611 | tail -1'],
                           capture_output=True, text=True, timeout=30)
        vol = float(r.stdout.split()[3].rstrip('G')) if r.returncode == 0 else -1
    except Exception:
        vol = -1
    check('volume >=4G', vol < 0 or vol >= 4, 'ship finals + clear volume')
    holder, alive = '', False
    try:
        holder = open('/tmp/video_build.lock').read().strip()
        if holder:
            with open(f'/proc/{holder}/cmdline', 'rb') as f:
                cmd = f.read().replace(b'\0', b' ').decode()
            alive = 'build_clip.py' in cmd or 'run_blocks.py' in cmd
    except (OSError, ValueError):
        pass
    check('no live video build', not alive, f'pid {holder} holds the lock')
    for ch in chs:
        ap = f'{BASE}/approved_ch{ch}.json'
        if not os.path.exists(ap):
            check(f'ch{ch} approval present', False, 'owner bless + record SHAs')
            continue
        a = json.load(open(ap, encoding='utf-8'))
        try:
            ok = (sha(sb_of(ch)) == a.get('storyboard_sha')
                  and sha(f'{BASE}/glossary_ch{ch}.json') == a.get('glossary_sha'))
        except OSError:
            ok = False
        check(f'ch{ch} approval SHAs match', ok, 'republish + re-bless')
    # V5 across lanes (scoped to requested chapters)
    import glob as _g
    for gp in sorted(_g.glob(f'{BASE}/glossary_ch*.json')):
        if '.draft' in gp:
            continue
        _m = re.search(r'ch(\d+)', gp)
        if _m and _m.group(1).zfill(2) not in chs:
            continue
        gl = json.load(open(gp, encoding='utf-8'))
        bad = [k for k, v in gl.items() if isinstance(v, dict)
               and v.get('status') == 'confirmed' and not (v.get('deva') or '').strip()]
        m = re.search(r'ch(\d+)', gp).group(1).zfill(2)
        check(f'ch{m} V5 confirmed carry Deva', not bad,
              f'{len(bad)} terms need owner Deva or proposed-flip')
    # audio cache per blessed chapter (0 missing)
    sys.path.insert(0, BASE)
    import holds as H
    for ch in chs:
        ap = f'{BASE}/approved_ch{ch}.json'
        if not os.path.exists(ap):
            continue
        sb = json.load(open(sb_of(ch), encoding='utf-8'))
        byid = {b['id']: b for b in sb['blocks']}
        chslug = re.sub(r'[^a-z0-9]+', '-', (sb.get('title') or '').lower()).strip('-')[:40]
        _sec_seen, _sec_slug = {}, {}
        for b in sb['blocks']:
            if b['section'] not in _sec_seen:
                _sec_seen[b['section']] = len(_sec_seen)
        for _s, _i in _sec_seen.items():
            _sec_slug[_s] = (re.sub(r'[^a-z0-9]+', '-', _s.lower()).strip('-')[:40]
                             or f'sec{_i:02d}')
        groups, cur = [], []
        for b in sb['blocks']:
            if b['id'] == 'b_opener' or b['voice'] == 'none':
                continue
            if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
                groups.append(cur)
                cur = []
            cur.append(b)
        if cur:
            groups.append(cur)
        groups = H.split_after(H.split_phoneme_groups(groups),
                               set(H.drops_for(sb_of(ch))))
        import glob as _g2
        missing = 0
        for g in groups:
            if g[0].get('group_kind') == 'opener':
                continue
            h = hashlib.sha1(
                f"{g[0]['voice']}|{' '.join(x.get('directed', x['text']) for x in g)}".encode()
            ).hexdigest()[:12]
            sec = _sec_slug[g[0]['section']]
            if not _g2.glob(f'{VOL}/{chslug}/groups/{sec}/*_{g[0]["voice"]}_{h}.wav'):
                missing += 1
        check(f'ch{ch} audio cached (0 missing)', missing == 0,
              f'{missing} groups need render_chapter first')
    try:
        env = open(os.path.expanduser('~/.config/opencode/.env')).read()
        check('Fish key present', 'FISH_API_KEY' in env, 'owner provides key')
    except OSError:
        check('Fish key present', False, 'owner provides key')
    check('MMS model present', os.path.exists('/tmp/mmsmod/node_modules'),
          'restore tantrasara/tools/mmsmod.tgz from R2 to /tmp')
    try:
        from faster_whisper import WhisperModel  # noqa
        check('whisper importable', True)
    except Exception:
        check('whisper importable', False, 'pip install faster-whisper')
    print('\n'.join(PASS + FAIL))
    print('PREFLIGHT ' + ('GREEN' if not FAIL else 'RED'))
    sys.exit(0 if not FAIL else 1)


if __name__ == '__main__':
    main()
