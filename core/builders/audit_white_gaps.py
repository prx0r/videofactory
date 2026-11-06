#!/usr/bin/env python3
"""White-gap antidote audit: prove no holdable Sanskrit hides in the white.

Usage: python3 audit_white_gaps.py <storyboard.json> [--max 60]

For every >max WHITE_GAP the hold-scan flags, this walks the actual spoken
words in that span and sorts every Sanskrit-ish word into exactly one bucket:

  BUG      — a CONFIRMED glossary term was spoken but no cue fired.
             This must be zero. A nonzero count is a cue-engine defect:
             fix the engine, never the data.
  PROPOSED — the word is glossary-proposed (white by design until the owner
             confirms). Known, tracked, not a defect.
  UNLISTED — Sanskrit-shaped word with no glossary key at all (no English
             gloss exists, so no card CAN render). Mining backlog, not a bug.
  CLEAN    — no Sanskrit-shaped word spoken: pure English exposition.

Exit 0 with a tally. Exit 2 if any BUG is found (and name it).
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))
WPM = 150.0


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def main():
    a = sys.argv[1:]
    sb_path = a[0]
    opt = dict(zip(a[1::2], a[2::2]))
    max_hold = float(opt.get('--max', '60').lstrip('=')) if '--max' in opt else 60.0
    import holds as _H
    lane = _H.lane_for(os.path.abspath(sb_path))
    sb = json.load(open(sb_path, encoding='utf-8'))
    gl = json.load(open(lane['glossary'], encoding='utf-8')) if os.path.exists(lane['glossary']) else {}
    conf = {k for k, v in gl.items() if isinstance(v, dict) and v.get('status') == 'confirmed'}
    prop = {k for k, v in gl.items() if isinstance(v, dict) and v.get('status') != 'confirmed'}
    blocks = [b for b in sb['blocks'] if b['id'] != 'b_opener' and b['voice'] != 'none']
    t, times = 0.99, {}
    for b in blocks:
        n = len(b['text'].split())
        times[b['id']] = (t, t + n / WPM * 60.0)
        t += n / WPM * 60.0 + 0.3

    r = subprocess.run([sys.executable, os.path.join(BASE, 'scan_holds.py'), sb_path,
                        '--max', str(max_hold)], capture_output=True, text=True)
    gaps = []
    for line in (r.stdout or '').splitlines():
        if line.startswith('FAIL hold') and 'WHITE_GAP' in line:
            m = re.search(r'(\d+)s>.*at (\d+)s \(block (b\d+)\)', line)
            if m:
                dur, start = int(m.group(1)), int(m.group(2))
                gaps.append((start, start + dur, m.group(3), line))

    def verse_key_match(w, keys):
        c = w.strip('.,!?;:\'"—-')
        if not c:
            return None
        f = fold(c)
        if f in keys:
            return f
        if re.search(r'[\u0900-\u097F]', c):
            try:
                f2 = fold(_H.to_iast(c))
                if f2 in keys:
                    return f2
            except Exception:
                pass
        return None

    # scan-identical cues (same loop, same break): a block either fired its
    # cue or it did not — no third interpretation, no drift between tools.
    cue_bids = {}
    for b in blocks:
        if b['type'] not in ('narration', 'dialogue', 'verse'):
            continue
        t0, t1 = times[b['id']]
        words = [w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        for ji, w in enumerate(words):
            if b['type'] == 'verse':
                key = verse_key_match(w, conf)
            else:
                f = fold(w.strip('.,!?;:\'"—-'))
                key = f if f in conf else None
            if key:
                cue_bids[b['id']] = key
                break  # one cue per block (builder rule)

    def key_of(w):
        raw = w.strip('.,!?;:\'"—-')
        if not raw:
            return None
        f = fold(raw)
        if f in conf or f in prop:
            return f
        if re.search(r'[\u0900-\u097F]', raw):
            try:
                f2 = fold(_H.to_iast(raw))
                if f2 in conf or f2 in prop:
                    return f2
            except Exception:
                pass
        sanskrit_shaped = bool(re.search(r'[\u0900-\u097F]', raw)) or (
            len(raw) >= 4 and bool(re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]', raw)))
        return raw if sanskrit_shaped else None

    bugs, proposed, unlisted, clean = [], [], [], []
    for start, end, bid, line in gaps:
        inspan = [b for b in blocks if times[b['id']][0] >= start - 1 and times[b['id']][0] < end]
        bwords, pwords, uwords = [], [], []
        for b in inspan:
            if b['type'] not in ('narration', 'dialogue', 'verse'):
                continue
            for w in b['text'].strip().split():
                if not re.search(r'\w', w, re.U):
                    continue
                k = key_of(w)
                if k is None:
                    continue
                if k in conf and b['id'] not in cue_bids:
                    # confirmed term spoken in a block that fired NO cue:
                    # the engine missed a holdable word — defect, fix now.
                    bwords.append((b['id'], w))
                elif k in prop:
                    pwords.append((b['id'], w))
                elif k not in conf:
                    uwords.append((b['id'], w))
        span = {'at': start, 'dur': end - start, 'bid': bid, 'line': line[:160]}
        if bwords:
            bugs.append(dict(span, words=bwords))
        elif pwords:
            proposed.append(dict(span, words=pwords[:6]))
        elif uwords:
            unlisted.append(dict(span, words=uwords[:6]))
        else:
            clean.append(dict(span))
    print(f'antidote audit {sb_path}: {len(gaps)} white gaps > {max_hold:.0f}s')
    print(f'  BUG (confirmed term spoken, no cue): {len(bugs)}')
    for g in bugs:
        print(f'    {g["at"]}s block {g["bid"]}: {g["words"]}')
    print(f'  PROPOSED (white by design): {len(proposed)}')
    print(f'  UNLISTED (no gloss exists — mining backlog): {len(unlisted)}')
    for g in unlisted:
        print(f'    {g["at"]}s block {g["bid"]}: {g["words"]}')
    print(f'  CLEAN (pure English exposition): {len(clean)}')
    out = opt.get('--json')
    if out:
        try:
            import factory_contract as _fc
            _unit = _fc.lane_paths(os.path.abspath(sb_path))['unit']
        except Exception:
            _unit = ((re.search(r'ch(\d+)', sb_path) or [None, '01'])[1] or '01')
        json.dump({'unit': _unit, 'gaps': len(gaps), 'bugs': bugs, 'proposed': proposed,
                   'unlisted': unlisted, 'clean': len(clean)}, open(out, 'w'), indent=1)
        print(f'wrote {out}')
    if bugs:
        print('ANTIDOTE RED — cue-engine defect, fix the engine')
        return 2
    print('ANTIDOTE GREEN — no holdable Sanskrit hides in the white')
    return 0


if __name__ == '__main__':
    sys.exit(main())
