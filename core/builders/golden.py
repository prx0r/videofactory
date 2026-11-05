#!/usr/bin/env python3
"""Golden store: the owner-blessed render is the reference; every future
render is mechanically compared against it.
Usage: python3 golden.py seal <ch> <video.mp4>    # after owner ears pass
       python3 golden.py check <ch> <video.mp4>   # in pipeline, after verify
seal stores golden/ch<NN>.json (committed): video sha, duration, cuts,
coverage map, cue sequence, verify summary.
check FAILS (exit 1) on: duration drift >2s, cue keys out of order or
missing, any cue time drift >3s, white_pct drift >5pp, cuts drift >2%.
Tolerances cover encoder nondeterminism only — anything bigger is a real
change and must be re-approved, never auto-accepted.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import json, os, subprocess, sys, hashlib

BASE = _vf.repo_root()
GOLD = f'{BASE}/golden'
os.makedirs(GOLD, exist_ok=True)

def ffprobe(p):
    r = subprocess.run(['ffprobe', '-v', 'error',
                        '-show_entries', 'format=duration,size',
                        '-of', 'json', p], capture_output=True, text=True, check=True)
    f = json.loads(r.stdout)['format']
    return float(f['duration']), int(f['size'])

def metrics(video):
    meta_p = os.path.splitext(video)[0] + '.render_meta.json'
    assert os.path.exists(meta_p), f'no render meta beside {video} — build_clip writes it'
    m = json.load(open(meta_p))
    dur, size = ffprobe(video)
    return {'video_sha': hashlib.sha256(open(video, 'rb').read()).hexdigest(),
            'duration': round(dur, 2), 'size': size, 'cuts': m['cuts'],
            'white_pct': m['white_pct'], 'coverage': m['coverage'],
            'cues': m['cues']}

def seal(ch, video):
    g = metrics(video)
    g['video'] = os.path.basename(video)
    json.dump(g, open(f'{GOLD}/ch{ch}.json', 'w'), indent=1)
    print(f'sealed golden/ch{ch}.json: {g["duration"]}s, {g["cuts"]} cuts, white {g["white_pct"]}%')
    print('commit it — the golden is law until the owner re-blesses.')

def check(ch, video):
    gp = f'{GOLD}/ch{ch}.json'
    if not os.path.exists(gp):
        print(f'no golden for ch{ch} — first approved render will seal it (PASS by default)')
        return
    g = json.load(open(gp))
    m = metrics(video)
    fails = []
    if abs(m['duration'] - g['duration']) > 2:
        fails.append(f"duration {g['duration']}s -> {m['duration']}s")
    gk = [c['key'] for c in g['cues']]; mk = [c['key'] for c in m['cues']]
    if gk != mk:
        fails.append(f'cue sequence changed: {gk} -> {mk}')
    else:
        for a, b in zip(g['cues'], m['cues']):
            if abs(a['t'] - b['t']) > 3:
                fails.append(f"cue {a['key']} drifted {a['t']}s -> {b['t']}s")
    if abs(m['white_pct'] - g['white_pct']) > 5:
        fails.append(f"white {g['white_pct']}% -> {m['white_pct']}%")
    if abs(m['cuts'] - g['cuts']) > max(2, 0.02 * g['cuts']):
        fails.append(f"cuts {g['cuts']} -> {m['cuts']}")
    if fails:
        print('GOLDEN FAIL:')
        [print(' -', f) for f in fails]
        raise SystemExit(1)
    print(f'GOLDEN PASS: ch{ch} matches blessed render '
          f'({m["duration"]}s, {m["cuts"]} cuts, white {m["white_pct"]}%)')

if __name__ == '__main__':
    cmd, ch = sys.argv[1], sys.argv[2].zfill(2)
    ({'seal': seal, 'check': check})[cmd](ch, sys.argv[3])
