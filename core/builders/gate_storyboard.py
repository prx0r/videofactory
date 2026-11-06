#!/usr/bin/env python3
"""Storyboard gate: fail the render BEFORE it runs (estimates, no audio).
Usage: python3 gate_storyboard.py <storyboard.json> [--glossary g.json]
Binary: green sheet, drops group-final with why, intro thumbnail <=60s,
H8 rhythm advisory (reported, never fails alone), confirmed terms carry
citation Deva, literals use square brackets. Exit 0 GREEN, 1 RED.
Estimates flag; measured onsets at the video gate decide finally.
"""
import json, os, re, sys, unicodedata

FAIL, PASS = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(f'{"PASS" if ok else "FAIL"} {name}' + (f' — {detail}' if detail else ''))


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


WPM = 150.0


def main():
    a = sys.argv[1:]
    sb_path = a[0]
    # ch06 files use the short name (storyboard_ch6.json), like run_all
    import glob as _gg0
    if not os.path.exists(sb_path) and 'ch06' in sb_path:
        _alt = sb_path.replace('ch06', 'ch6')
        if os.path.exists(_alt):
            sb_path = _alt
    opt = dict(zip(a[1::2], a[2::2]))
    sb = json.load(open(sb_path, encoding='utf-8'))
    ch = (re.search(r'ch(\d+)', sb_path) or [None, '01'])[1].zfill(2)

    v = sb.get('validation', {})
    check('D1 storyboard green', not v.get('errors') and not v.get('warnings'),
          f"{len(v.get('errors', []))}e {len(v.get('warnings', []))}w")

    blocks = [b for b in sb['blocks'] if b['id'] != 'b_opener' and b['voice'] != 'none']
    # groups, same rule as every builder
    groups, cur = [], []
    for b in blocks:
        if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)
    import sys as _sys
    _sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
    import holds as _H
    groups = _H.split_phoneme_groups(groups)

    # drops: exist, justified, group-final (M6 computable without audio)
    import glob as _gg
    dp = os.path.join(os.path.dirname(os.path.abspath(sb_path)), f'drops_ch{ch}.json')
    if os.path.exists(dp):
        d = json.load(open(dp, encoding='utf-8'))
        have = {b['id'] for g in groups for b in g}
        for bid, spec in d.items():
            check(f'drop {bid} in render', bid in have)
            if bid in have:
                gg = next(g for g in groups if any(x['id'] == bid for x in g))
                check(f'drop {bid} group-final (M6)', gg[-1]['id'] == bid)
            check(f'drop {bid} justified', isinstance(spec, dict)
                  and spec.get('pause', 0) > 0 and (spec.get('why') or '').strip())
    else:
        check('drops file (none filed)', True, 'no owner drops')

    # glossary discipline (lane-aware: shiva units resolve shiva glossaries)
    gl = {}
    if opt.get('--glossary'):
        glp = opt['--glossary']
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import holds as _H
        try:
            glp = _H.lane_for(os.path.abspath(sb_path))['glossary']
        except Exception:
            glp = os.path.join(
                os.path.dirname(os.path.abspath(sb_path)), f'glossary_ch{ch}.json')
    if os.path.exists(glp):
        gl = json.load(open(glp, encoding='utf-8'))
        bad_key = [k for k in gl if k != fold(k)]
        check('D3 keys folded ASCII', not bad_key, str(bad_key[:3]))
        conf = [k for k, vv in gl.items() if isinstance(vv, dict) and vv.get('status') == 'confirmed']
        nodeva = [k for k in conf if not gl[k].get('deva')]
        check('V5 confirmed terms carry citation Deva', not nodeva, str(nodeva[:3]))
        nogloss = [k for k in conf if not (gl[k].get('gloss') or '').strip()]
        check('V5b confirmed terms carry gloss (no bulk-confirm empties)', not nogloss, str(nogloss[:5]))
        machine = [k for k in conf if gl[k].get('deva_status') in ('machine', 'machine-lossy')]
        check('V5c no machine Deva confirmed (owner pass required)', not machine, str(machine[:5]))
        paren = [k for k in conf if '(' in gl[k].get('literal', '') or ')' in gl[k].get('literal', '')]
        check('V7 literals use square brackets', not paren, str(paren[:3]))
        # list geometry: run-based, renderer-identical (the old
        # preflight_list_geometry worst-case-5 model false-failed ch20 by
        # stacking cards that never co-occur and fattening test cards with
        # an unconfirmed literal). Advisory from video entry; recorded here.
        try:
            import factory_contract as _fcg
            _fcg.require_list_geometry(sb_path)
            check('H-list geometry fits above subtitles', True)
        except Exception as exc:
            check('H-list geometry fits above subtitles', False, str(exc)[:300])
    else:
        check('glossary present', False, glp)

    # timing estimates @150wpm (+0.3s flow bed per block, bell 0.99)
    t, times = 0.99, {}
    for b in blocks:
        n = len(b['text'].split())
        times[b['id']] = (t, t + n / WPM * 60.0)
        t += n / WPM * 60.0 + 0.3

    def is_break(b, prev):
        if b['type'] == 'verse' or b['type'] == 'dialogue':
            return True
        if b.get('directed', '').startswith('[long pause]'):
            return True
        return prev is not None and b['section'] != prev['section']

    first = blocks[0] if blocks else None
    intro_end = next((b for b in blocks[1:] if is_break(b, first)), None)
    intro_dur = (times[intro_end['id']][0] - 0.0) if intro_end else t
    # A unit whose whole content IS the intro (series opener: no chant, no
    # section break) is intro-only by nature — the thumbnail holding it is
    # data, not a defect (s00/shiva H1 precedent).
    _has_break = intro_end is not None
    check('H1 intro thumbnail <=60s', (not _has_break) or intro_dur <= 60,
          f'intro to {intro_end["id"] if intro_end else "end"} ≈ {intro_dur:.0f}s')

    # H8: hold-change simulation (thumbnail, verse, cues clamped at next
    # cue/event, persist singles) — max unchanged stretch. Builder rule:
    # EVERY term mention fires at its own onset (re-mentions re-fire),
    # INCLUDING verse chants (postmortem fix: verse Devanagari/IAST terms
    # hold as term cards after the chant while granny continues).
    conf = {k for k, vv in gl.items() if isinstance(vv, dict) and vv.get('status') == 'confirmed'}
    try:
        import holds as _H2
        _to_iast = _H2.to_iast
    except Exception:
        _to_iast = lambda s: s

    def _vkey(w):
        c = w.strip('.,!?;:\'"—-')
        f = fold(c)
        if f in conf:
            return f
        if re.search(r'[\u0900-\u097F]', c):
            try:
                f2 = fold(_to_iast(c))
                if f2 in conf:
                    return f2
            except Exception:
                pass
        return None

    cues = []
    for b in blocks:
        if b['type'] not in ('narration', 'dialogue', 'verse'):
            continue
        t0, t1 = times[b['id']]
        _split = [w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        for _ji, w in enumerate(_split):
            # verse: Devanagari/IAST transliterated then folded; narration:
            # folded directly. ONE cue per block (first match) — exactly the
            # renderer's rule (build_clip breaks per block); every-mention
            # counting invents stacks the renderer never shows.
            if b['type'] == 'verse':
                c = _vkey(w)
            else:
                f = fold(w.strip('.,!?;:\'"—-'))
                c = f if f in conf else None
            if c:
                # estimate: word onset by position (measured onsets decide)
                cues.append((t0 + (t1 - t0) * _ji / max(1, len(_split)), b['id'], c))
                break
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
    first_verse_t = min([times[b['id']][0] for b in blocks if b['type'] == 'verse'], default=None)
    # every visual change: thumbnail end, cue starts, verse onsets,
    # tone-break white returns, and the end
    intro_end_t = (times[intro_end['id']][0] if intro_end else t)
    marks = sorted(set([0.0, intro_end_t, t] + [s for s, _, _ in cues] + ev))
    worst, worst_d = None, 0.0
    for i in range(len(marks) - 1):
        d = marks[i + 1] - marks[i]
        if d > worst_d:
            worst_d, worst = d, (marks[i], marks[i + 1])
    check('H8 visual rhythm advisory (never fails alone)', True,
          f'max unchanged ≈ {worst_d:.0f}s at {worst[0]:.0f}s' if worst else 'empty')
    if worst_d > 60:
        over = sorted([(round(e - s), k) for s, e, k in spans if e - s > 60],
                      reverse=True)[:5]
        for d, k in over:
            print(f'INFO stuck card {k} ≈ {d}s')

    print('\n'.join(PASS + FAIL))
    print('GATE ' + ('GREEN' if not FAIL else 'RED'))
    sys.exit(0 if not FAIL else 1)


if __name__ == '__main__':
    main()
