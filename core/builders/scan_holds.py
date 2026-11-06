#!/usr/bin/env python3
"""Hold-scan: find any visual hold past ~60s and explain WHY (not just where).

Usage: python3 scan_holds.py <storyboard.json> [--glossary g.json] [--max 60]

Owner law: max hold for anything is caught in the storyboard.png (contact
sheet / timeline estimate) and max 60s. Anything over means look for bugs —
the classic is: verse voice chants a Devanagari/IAST term but no term card
fires (cues only watched narration/dialogue), so granny continues over
white or a stale hold while the just-chanted term never appears.

For each >max span the scan reports:
- kind: WHITE_GAP (no card) vs STUCK_TERM (one term held) vs STUCK_VERSE_HOLD
- span blocks + seconds (estimates @150wpm; measured onsets decide at render)
- reasoning: preceding verse term unheld? proposed-not-confirmed? re-mention
  never re-fires? no cue/event in span?
Exit 1 with FAIL lines when any span exceeds max (storyboard.png gate).
"""
import json
import os
import re
import sys
import unicodedata

WPM = 150.0


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def to_iast_safe(s):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import holds as _H
        return _H.to_iast(s)
    except Exception:
        return s


def verse_key_match(word, conf):
    """Match a verse word (Devanagari or IAST) to a folded glossary key."""
    c = word.strip('.,!?;:\'"—-')
    if not c:
        return None
    # roman path: fold directly
    f = fold(c)
    if f in conf:
        return f
    # devanagari path: transliterate then fold
    if re.search(r'[\u0900-\u097F]', c):
        try:
            f2 = fold(to_iast_safe(c))
            if f2 in conf:
                return f2
        except Exception:
            pass
    return None


def main():
    a = sys.argv[1:]
    sb_path = a[0]
    opt = dict(zip(a[1::2], a[2::2]))
    max_hold = float(opt.get('--max', '60').lstrip('=')) if '--max' in opt else 60.0
    sb = json.load(open(sb_path, encoding='utf-8'))
    ch = (re.search(r'ch(\d+)', sb_path) or [None, '01'])[1].zfill(2)
    if opt.get('--glossary'):
        glp = opt['--glossary']
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import holds as _H
        try:
            glp = _H.lane_for(os.path.abspath(sb_path))['glossary']
        except Exception:
            glp = os.path.join(os.path.dirname(os.path.abspath(sb_path)), f'glossary_ch{ch}.json')
    gl = json.load(open(glp, encoding='utf-8')) if os.path.exists(glp) else {}
    conf = {k for k, v in gl.items() if isinstance(v, dict) and v.get('status') == 'confirmed'}
    prop = {k for k, v in gl.items() if isinstance(v, dict) and v.get('status') != 'confirmed'}

    blocks = [b for b in sb['blocks'] if b['id'] != 'b_opener' and b['voice'] != 'none']
    t, times = 0.99, {}
    for b in blocks:
        n = len(b['text'].split())
        times[b['id']] = (t, t + n / WPM * 60.0)
        t += n / WPM * 60.0 + 0.3

    # cues: EVERY term mention fires at its own onset — narration, dialogue
    # AND verse (the fix: verse chants hold as term cards after the chant).
    # One cue per block (first matching word), word-onset estimated.
    cues = []
    verse_terms = {}  # bid -> key for verse blocks chanting a glossary term
    for b in blocks:
        if b['type'] not in ('narration', 'dialogue', 'verse'):
            continue
        t0, t1 = times[b['id']]
        words = [w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        for ji, w in enumerate(words):
            if b['type'] == 'verse':
                key = verse_key_match(w, conf)
            else:
                key = fold(w.strip('.,!?;:\'"—-'))
                key = key if key in conf else None
            if key:
                cues.append((t0 + (t1 - t0) * ji / max(1, len(words)), b['id'], key))
                if b['type'] == 'verse':
                    verse_terms[b['id']] = key
                break  # one cue per block (builder rule)

    ev = sorted(set([times[b['id']][0] for b in blocks
                     if b['type'] in ('verse', 'title', 'figure', 'dialogue')
                     or b.get('directed', '').startswith('[long pause]')]))

    def nxt(t0):
        for e in ev:
            if e > t0 + 0.05:
                return e
        return t

    spans = [[s, nxt(s), k] for s, _, k in cues]
    spans.sort()
    for i in range(len(spans) - 1):
        spans[i][1] = min(spans[i][1], spans[i + 1][0])

    def is_break(b, prev):
        if b['type'] == 'verse' or b['type'] == 'dialogue':
            return True
        if b.get('directed', '').startswith('[long pause]'):
            return True
        return prev is not None and b['section'] != prev['section']

    first = blocks[0] if blocks else None
    intro_end = next((b for b in blocks[1:] if is_break(b, first)), None)
    intro_end_t = (times[intro_end['id']][0] if intro_end else t)
    marks = sorted(set([0.0, intro_end_t, t] + [s for s, _, _ in cues] + ev))

    fails, infos = [], []
    for i in range(len(marks) - 1):
        s, e = marks[i], marks[i + 1]
        d = e - s
        if d <= max_hold:
            continue
        # what shows during (s,e)? newest cue covering s, else verse persist, else white
        covering = [k for cs, ce, k in spans if cs <= s < ce]
        kind = f'STUCK_TERM {covering[-1]}' if covering else 'WHITE_GAP'
        # reasoning: look back for verse terms that never fired
        s_bid = next((b['id'] for b in blocks if times[b['id']][0] <= s < times[b['id']][1]), '?')
        burst = [b for b in blocks if times[b['id']][0] <= s < times[b['id']][1]]
        reason = []
        # any verse in the last few blocks chanting a confirmed term with no cue?
        idx = next((ix for ix, b in enumerate(blocks) if b['id'] == s_bid), 0)
        window = blocks[max(0, idx - 6):idx + 1]
        for wb in window:
            if wb['type'] != 'verse':
                continue
            for w in wb['text'].strip().split():
                vk = verse_key_match(w, conf)
                if vk and wb['id'] not in verse_terms:
                    reason.append(f'verse {wb["id"]} chants {vk} but no cue fired (BUG)')
                    break
                if vk and wb['id'] in verse_terms:
                    reason.append(f'verse {wb["id"]} chants {vk} → held as term (fixed path)')
                    break
            # proposed verse terms never render
            for w in wb['text'].strip().split():
                vk = verse_key_match(w, prop)
                if vk:
                    reason.append(f'verse {wb["id"]} chants {vk} but proposed — white by design')
                    break
        if not reason:
            if kind.startswith('WHITE'):
                reason.append('no cue/event in span — check proposed-vs-confirmed or missing verse-term cue')
            else:
                reason.append('single term held — no superseding cue/event; needs draw/overlay/release per 60s law')
        fails.append(f'FAIL hold {d:.0f}s>{max_hold:.0f}s [{kind}] at {s:.0f}s (block {s_bid}): {"; ".join(reason)}')
        infos.append((s, e, kind, s_bid, reason))

    print(f'scan {sb_path}: {len(cues)} cues ({sum(1 for _, bid, _ in cues if bid in verse_terms)} from verse), '
          f'{len([m for m in marks])} marks, max gap {max([marks[i+1]-marks[i] for i in range(len(marks)-1)], default=0):.0f}s')
    if verse_terms:
        print(f'verse-term holds: {", ".join(f"{bid}→{k}" for bid, k in sorted(verse_terms.items())[:12])}'
              + (f' (+{len(verse_terms)-12} more)' if len(verse_terms) > 12 else ''))
    for f in fails:
        print(f)
    print('SCAN ' + ('RED' if fails else 'GREEN'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
