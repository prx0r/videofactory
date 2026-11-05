#!/usr/bin/env python3
"""Chapter -> group-aligned video chunk parts (canonical chunk method).
Usage: python3 run_blocks.py <storyboard.json> <outdir> [max_secs=600]
Groups are the audio atoms (content-hash cache — audio renders once, never
re-renders); chunks are ranges of whole groups only (M6). Ranges never end
on an owner drop group (the pause bed needs the next group in range).
Writes <outdir>/pN.mp4 + concat.txt. Verify the ASSEMBLED chapter after.
"""
import json, os, re, subprocess, sys, hashlib, glob

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import holds as H

LOCK = '/tmp/video_build.lock'


def _holder_alive(pid):
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode()
        return ('build_clip.py' in cmd or 'run_blocks.py' in cmd
                or 'overnight.py' in cmd)
    except (OSError, ValueError):
        return False


def claim_lock():
    me = str(os.getpid())
    try:
        with open(LOCK) as f:
            holder = f.read().strip()
        if holder and holder != me and _holder_alive(holder):
            sys.exit(f'video lock held by pid {holder} — one build at a time (M21)')
    except OSError:
        pass
    with open(LOCK, 'w') as f:
        f.write(me)
    import atexit

    def _release():
        try:
            with open(LOCK) as f:
                if f.read().strip() == me:
                    os.remove(LOCK)
        except OSError:
            pass
    atexit.register(_release)


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40]


def main():
    # no lock here: build_clip claims per range (parent must never hold
    # what its child checks — it would refuse its own parent).
    sb_path, outdir = sys.argv[1], sys.argv[2]
    cap = float(sys.argv[3]) if len(sys.argv) > 3 else 600.0
    sb = json.load(open(sb_path, encoding='utf-8'))
    byid = {b['id']: b for b in sb['blocks']}
    ch = slug(sb.get('title', 'chapter')) or 'chapter'
    lane = H.lane_for(sb_path)
    gl = json.load(open(lane['glossary'], encoding='utf-8')) if os.path.exists(lane['glossary']) else {}
    gl = {k: v for k, v in gl.items() if isinstance(v, dict) and v.get('status') == 'confirmed'}
    groups, cur = [], []
    for b in sb['blocks']:
        if b['id'] == 'b_opener':
            continue
        if b['voice'] == 'none':
            continue
        if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)
    _drops = set(H.drops_for(sb_path))
    groups = H.split_after(H.split_phoneme_groups(groups), _drops)
    sec_seen = {}
    for b in sb['blocks']:
        if b['section'] not in sec_seen:
            sec_seen[b['section']] = len(sec_seen)
    sec_slug = {s: (slug(s) or f'sec{i:02d}') for s, i in sec_seen.items()}
    vols = _vf.renders_root()

    def gdur(g):
        # estimate from chars (no mount I/O here — the mount flakes and
        # ffprobes stall; build_clip measures real durations at build).
        # ~15 chars/sec English, ~8 Sanskrit-heavy; ranges are soft caps.
        n = sum(len(x.get('directed', x['text'])) for x in g)
        rate = 8.0 if g[0]['voice'] == 'verse' else 15.0
        return n / rate

    def ends_on_drop(rg):
        return any(b['id'] in _drops for b in rg[-1]) if rg else False

    ranges, cur_r, cur_d = [], [], 0.0
    for g in groups:
        d = gdur(g)
        if cur_r and cur_d + d > cap and not ends_on_drop(cur_r):
            ranges.append(cur_r)
            cur_r, cur_d = [], 0.0
        cur_r.append(g)
        cur_d += d
    if cur_r:
        ranges.append(cur_r)
    print(f'chapter={ch} groups={len(groups)} ranges={len(ranges)}')
    os.makedirs(outdir, exist_ok=True)
    parts = []
    for i, rg in enumerate(ranges):
        bids = [b['id'] for g in rg for b in g]
        out = os.path.join(outdir, f'p{i:02d}.mp4')
        # resume: a part with its render meta already built is finished —
        # never rebuild finished work (M28: lost ch06 parts to a restart).
        if (os.path.exists(out) and os.path.exists(os.path.splitext(out)[0] + '.render_meta.json')
                and os.path.getsize(out) > 1000000):
            print(f'range {i}: {bids[0]}..{bids[-1]} ({len(bids)} blocks) -> {out} CACHED', flush=True)
            parts.append(out)
            continue
        print(f'range {i}: {bids[0]}..{bids[-1]} ({len(bids)} blocks) -> {out}', flush=True)
        subprocess.run(['python3', f'{BASE}/build_clip.py', sb_path, ','.join(bids), out], check=True)
        parts.append(out)
    with open(os.path.join(outdir, 'concat.txt'), 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    print(f'parts={len(parts)} concat-list ready (concat + verify as assembly)')
    print(json.dumps({'chapter': ch, 'ranges': len(ranges), 'parts': parts}))


if __name__ == '__main__':
    main()
