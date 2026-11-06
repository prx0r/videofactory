#!/usr/bin/env python3
"""Stack-crash predictor: find list-stacks that WILL crash the video build.

Root cause it locks (ch16 p02 precedent, 2026-11-06): build_clip fires
EVERY matching word as a cue (its per-word-row loop defeats the
documented one-cue-per-block rule), so one block chanting several long
compounds forms a same-block run; render_list then collides with the
subtitle zone and the part dies mid-render. The entry gate
(require_list_geometry) models one cue per block, so it cannot see the
run coming.

This checker replays the RENDERER's cue rule (every matching word fires,
shared fold/to_iast/verse_match_key — never re-implemented) on estimated
timings, chains cues exactly like build_clip (exact-touch, newest
clamping), and tests every progressive stack prefix of every run with
the REAL holds.render_list (the single implementation the renderer
calls) — but only INSIDE one video part at a time. Part ranges replicate
run_blocks chunking exactly (same-section same-voice atoms,
split_phoneme_groups + split_after(drops), char-estimated ~15/s English /
~8/s verse soft cap 600s; shared H helpers, formula cited from
run_blocks.py). A cross-part run never co-renders, so it is not tested.

Limits (stated, not hidden): timings are estimates — measured MMS onsets
can split a predicted run (false alarm → owner waives) or, in principle,
join one the estimates split (the entry gate has the same estimate
limit; measured decides at render). Word splits are 1:1 asserted by the
aligner. Provenance: 14/14 rendered units (01-15) predict clean;
ch16 predicts the exact crashing keys.

Usage: python3 check_stacks.py <storyboard.json>
check_issues.py imports predict() and files one `stack-crash` issue per
colliding run (severity block: rendering would burn hours then die;
waive with owner reason if estimates are wrong).
"""
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))

import holds as H

WPM = 150.0


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def confirmed_gl(sb_path):
    """Mirror build_clip's _gl exactly (confirmed + gloss, literal only
    when literal_status is confirmed). Same 6-line rule as
    require_list_geometry; queued post-drain: single confirmed_gl() shared
    helper (holds.py/factory_contract.py are provenance-pinned now)."""
    lane = H.lane_for(os.path.abspath(sb_path))
    raw = json.load(open(lane['glossary'], encoding='utf-8')) if os.path.exists(lane['glossary']) else {}
    gl = {}
    for k, v in (raw or {}).items():
        if not (isinstance(v, dict) and v.get('status') == 'confirmed' and v.get('gloss')):
            continue
        gl[k] = {'deva': v.get('deva', ''), 'gloss': v.get('gloss', ''),
                 'literal': v.get('literal', '') if v.get('literal_status') == 'confirmed' else ''}
    return gl


def part_ranges(blocks, sb_path):
    """Replicate run_blocks chunking (ranges of bid-lists). Groups are
    same-section same-voice atoms (opener/none skipped), phoneme-carved,
    drop-split — then accumulated to the char-estimated soft cap
    (~15 chars/s English, ~8/s verse)."""
    groups, cur = [], []
    for b in blocks:
        if b['id'] == 'b_opener' or b.get('voice') == 'none':
            continue
        if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)
    groups = H.split_after(H.split_phoneme_groups(groups), set(H.drops_for(sb_path)))

    def gdur(g):
        n = sum(len(x.get('directed', x['text'])) for x in g)
        return n / (8.0 if g[0]['voice'] == 'verse' else 15.0)

    ranges, cur_r, cur_d = [], [], 0.0
    for g in groups:
        d = gdur(g)
        if cur_r and cur_d + d > 600.0:
            ranges.append([b['id'] for gg in cur_r for b in gg])
            cur_r, cur_d = [], 0.0
        cur_r.append(g)
        cur_d += d
    if cur_r:
        ranges.append([b['id'] for gg in cur_r for b in gg])
    return ranges


def _verse_key(w, conf):
    c = w.strip('.,!?;:\'"—-')
    if not c:
        return None
    f = _fold(c)
    if f in conf:
        return f
    if re.search(r'[\u0900-\u097F]', c):
        try:
            f2 = _fold(H.to_iast(c))
            if f2 in conf:
                return f2
        except Exception:
            pass
    return None


def predict(sb_path):
    """Return [{bids, keys, detail}] — one per colliding stack run."""
    sb = json.load(open(sb_path, encoding='utf-8'))
    blocks = sb['blocks']
    by_id = {b['id']: b for b in blocks}
    gl = confirmed_gl(sb_path)
    conf = set(gl)
    spoken = [b for b in blocks if b['id'] != 'b_opener' and b.get('voice') != 'none']
    t, times = 0.99, {}
    for b in spoken:
        n = len(b['text'].split())
        times[b['id']] = (t, t + n / WPM * 60.0)
        t += n / WPM * 60.0 + 0.3
    # renderer rule: EVERY matching word fires its own cue
    cues = []
    for b in spoken:
        if b['type'] not in ('narration', 'dialogue', 'verse'):
            continue
        t0, t1 = times[b['id']]
        words = [w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        for ji, w in enumerate(words):
            if b['type'] == 'verse':
                key = _verse_key(w, conf)
            else:
                key = _fold(w.strip('.,!?;:\'"—-'))
                key = key if key in conf else None
            if key:
                cues.append((t0 + (t1 - t0) * ji / max(1, len(words)), b['id'], key))
    ev = sorted(set([times[b['id']][0] for b in spoken
                     if b['type'] in ('verse', 'title', 'figure', 'dialogue')
                     or b.get('directed', '').startswith('[long pause]')]))

    def nxt(t0):
        for e in ev:
            if e > t0 + 0.05:
                return e
        return t

    spans = sorted([[s, min(nxt(s), 1e18), k, bid] for s, bid, k in cues])
    for i in range(len(spans) - 1):
        spans[i][1] = min(spans[i][1], spans[i + 1][0])
    # chain only inside one part (cross-part runs never co-render)
    part_of = {}
    for ri, r in enumerate(part_ranges(blocks, sb_path)):
        for bid in r:
            part_of.setdefault(bid, ri)
    out = []
    cur = []
    for i, sp in enumerate(spans):
        cur.append(sp)
        touched = i + 1 < len(spans) and abs(sp[1] - spans[i + 1][0]) < 1e-9
        same_part = (touched and part_of.get(spans[i + 1][3], -1) == part_of.get(sp[3], -2)
                     and all(part_of.get(x[3], -1) == part_of.get(cur[0][3], -2) for x in cur))
        if not same_part:
            if len(cur) >= 2:
                keys = [k for s, e, k, bid in cur]
                bids = [bid for s, e, k, bid in cur]
                for p in range(2, len(keys) + 1):
                    win = keys[max(0, p - 5):p]
                    try:
                        H.render_list(win, {k: gl[k] for k in win})
                    except AssertionError as exc:
                        out.append({'bids': sorted(set(bids), key=bids.index),
                                            'keys': win,
                                            'detail': f'stack will crash the build: {win} '
                                                      f'({str(exc)[:160]}) — split the list, demote a term, '
                                                      f'or waive with owner reason'})
                        break
            cur = []
    return out


def main():
    res = predict(sys.argv[1])
    print(f'stack check: {len(res)} colliding runs')
    for r in res:
        print(f"  {r['bids']}: {r['detail'][:220]}")
    print('STACKS ' + ('RED' if res else 'GREEN'))


if __name__ == '__main__':
    main()
