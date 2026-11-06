#!/usr/bin/env python3
"""Binary render-stage gate (GATES.md machine lines). Exit 0 all-green,
exit 1 with FAIL lines otherwise. Eye lines are read off proof PNGs.
Usage: gate_visual.py <storyboard.json> [--glossary g.json] [--meta render_meta.json]
  [--mp4 clip.mp4] [--subs subs.json] [--verify verify.json] [--approved approved.json]
"""
import json, os, re, subprocess, sys, unicodedata, glob

FAIL = []
PASS = []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(f'{"PASS" if ok else "FAIL"} {name}' + (f' — {detail}' if detail else ''))


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def main():
    a = sys.argv[1:]
    sb_path = a[0]
    opt = dict(zip(a[1::2], a[2::2]))
    sb = json.load(open(sb_path, encoding='utf-8'))
    ch = (re.search(r'ch(\d+)', sb_path) or [None, '01'])[1].zfill(2)

    # D1 storyboard green
    v = sb.get('validation', {})
    check('D1 storyboard green', not v.get('errors') and not v.get('warnings'),
          f"{len(v.get('errors', []))}e {len(v.get('warnings', []))}w")

    # D2 approval SHAs
    if '--approved' in opt:
        import hashlib
        ap = json.load(open(opt['--approved'], encoding='utf-8'))
        ok = True
        for key, path in (('storyboard_sha', sb_path),):
            h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
            ok = ok and h == ap.get(key)
        glp = os.path.join(os.path.dirname(os.path.abspath(sb_path)), f'glossary_ch{ch}.json')
        if os.path.exists(glp):
            h = hashlib.sha256(open(glp, 'rb').read()).hexdigest()
            ok = ok and h == ap.get('glossary_sha')
        check('D2 approval SHAs match', ok)
    else:
        check('D2 approval present', False, 'no --approved given (render gate closed)')

    # D3 + V5 + V7 glossary discipline (missing glossary fails —
    # a render with no glossary shows no term cards at all)
    gl = {}
    if '--glossary' in opt:
        gl = json.load(open(opt['--glossary'], encoding='utf-8'))
        bad_key = [k for k in gl if k != fold(k)]
        check('D3 keys folded ASCII', not bad_key, str(bad_key[:3]))
        conf = [k for k, vv in gl.items() if isinstance(vv, dict) and vv.get('status') == 'confirmed']
        nodeva = [k for k in conf if not (isinstance(gl[k], dict) and gl[k].get('deva'))]
        check('V5 confirmed terms carry citation Deva', not nodeva, str(nodeva[:3]))
        nogloss = [k for k in conf if not ((gl[k].get('gloss') or '').strip())]
        check('V5b confirmed terms carry gloss (no bulk-confirm empties)', not nogloss, str(nogloss[:5]))
        machine = [k for k in conf if gl[k].get('deva_status') in ('machine', 'machine-lossy')]
        check('V5c no machine Deva confirmed (owner pass required)', not machine, str(machine[:5]))
        paren = [k for k in conf if isinstance(gl[k], dict) and ('(' in gl[k].get('literal', '') or ')' in gl[k].get('literal', ''))]
        check('V7 literals use square brackets', not paren, str(paren[:3]))
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import holds as _H
            _H.preflight_list_geometry(gl)
            check('H-list geometry fits above subtitles', True)
        except Exception as exc:
            check('H-list geometry fits above subtitles', False, str(exc)[:300])
    else:
        check('glossary resolved (no term cards without it)', False, 'no --glossary given')

    # H3 render_meta cues match storyboard run scan
    if '--meta' in opt:
        m = json.load(open(opt['--meta'], encoding='utf-8'))
        # H4 is advisory only (owner order 2026-11-04 "get them live", upheld
        # 2026-11-06: white is a data state, never a defect; H8 + ears own
        # pacing). The number is still reported for the record.
        check('H4 white within band (advisory, never gates)', True,
              f"white {m.get('white_pct')}%")
        _starts_top = not m.get('bids') or m['bids'][0] == 'b1'
        if _starts_top:
            check('H1 thumbnail opens', m.get('coverage', {}).get('thumbnail', 0) > 0)
        else:
            check('H1 mid-chapter opens white (no intro re-show)', True,
                  'starts at ' + (m.get('bids', ['?'])[0]))
        mcues = [c['key'] for c in m.get('cues', [])]
        # recompute expected cue order from storyboard + confirmed glossary,
        # restricted to the rendered bid range when the meta records it
        # (segments carry their bids; full chapters carry all)
        sb_blocks = sb['blocks']
        if m.get('bids'):
            have = set(m['bids'])
            sb_blocks = [b for b in sb_blocks if b['id'] in have or b['id'] == 'b_opener']
        terms = {k for k, vv in gl.items() if isinstance(vv, dict) and vv.get('status') == 'confirmed'} if gl else set()
        # renderer rule: ONE cue per block (first matching word), narration
        # AND verse (verse chants fire term cues too — postmortem fix).
        # Mirrors build_clip exactly, or H3 invents cues/flags real ones.
        import sys as _sysv
        _sysv.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import holds as _Hv
            _to_iast_v = _Hv.to_iast
        except Exception:
            _to_iast_v = lambda s: s
        exp = []
        for b in sb_blocks:
            if b.get('type') not in ('narration', 'dialogue', 'verse'):
                continue
            # builder-exact tokenization: whitespace split, \w filter
            # (glued em-dash pairs do NOT split — matches build_clip).
            for w in b['text'].strip().split():
                if not re.search(r'\w', w, re.U):
                    continue
                raw = w.strip('.,!?;:\'"—-')
                if b.get('type') == 'verse':
                    c = fold(raw)
                    if c not in terms and re.search(r'[\u0900-\u097F]', raw):
                        try:
                            c = fold(_to_iast_v(raw))
                        except Exception:
                            pass
                    c = c if c in terms else None
                else:
                    c = fold(raw)
                    c = c if c in terms else None
                if c:
                    exp.append(c)
                    break
        check('H3 cue order matches storyboard', mcues == exp, f'{len(mcues)} cues')
        # drops: every filed drop applied in the render (lane-aware path —
        # a unit with no drops file validates against NOTHING, never
        # another chapter's file; shiva lane resolves shiva drops).
        _dp = None
        try:
            import holds as _Hd
            _dp = _Hd.lane_for(os.path.abspath(sb_path)).get('drops')
        except Exception:
            _dp = None
        if _dp is None or not os.path.exists(_dp):
            check('H7 drops applied', True, 'no drops file for this unit')
        else:
            _dfile = json.load(open(_dp, encoding='utf-8'))
            _dmeta = m.get('drops', {})
            # chunk-scoped: only drops rendered in this range's bids
            # can apply here; the rest belong to sibling chunks.
            _rbids = set(m.get('bids', []))
            _in_range = {k for k in _dfile if not _rbids or k in _rbids}
            # a group-final drop mid-group in this part means build_clip
            # would have split it — trust the renderer's own applied set
            # and only fail when a filed in-range drop was silently lost.
            check('H7 drops applied', _in_range <= set(_dmeta),
                  f'file={sorted(_in_range)} meta={sorted(_dmeta)}')
            check('H7 every drop justified', all(
                isinstance(v, dict) and v.get('pause', 0) > 0 and (v.get('why') or '').strip()
                for v in _dfile.values()), 'pause>0 + non-empty why required')
    else:
        check('H3/H4 render_meta present', False, 'no --meta given')

    # H5/H6 subtitle dump scan
    if '--subs' in opt and '--meta' in opt:
        subs = json.load(open(opt['--subs'], encoding='utf-8'))
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
            from factory_contract import validate_schema as _vs
            _vs('subtitles', subs, opt['--subs'])
        except Exception as exc:
            print(f'FAIL subtitle contract — {exc}\nGATE RED')
            sys.exit(1)
        deva_leak = [s for s in subs if re.search(r'[\u0900-\u097F]', s.get('s', ''))]
        check('H5 no Devanagari in subtitles', not deva_leak, f'{len(deva_leak)} leaks')
        selected = set(m['bids'])
        expected_words = [(b['id'], w) for b in sb['blocks']
                          if b['id'] in selected and b['voice'] != 'none'
                          for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        actual_words = [(row['bid'], row['w']) for row in subs]
        times = [row['t'] for row in subs]
        check('H6 subtitles cover spoken words in order', actual_words == expected_words
              and times == sorted(times) and (not times or times[-1] <= m['duration'] + 0.1),
              f'{len(actual_words)}/{len(expected_words)} word rows')
    elif '--subs' in opt:
        subs = json.load(open(opt['--subs'], encoding='utf-8'))
        deva_leak = [s for s in subs if re.search(r'[\u0900-\u097F]', s.get('s', ''))]
        check('H5 no Devanagari in subtitles', not deva_leak, f'{len(deva_leak)} leaks')
    else:
        check('H5/H6 subs dump present', False, 'no --subs given')

    # V1/A2 streams via verify report or ffprobe
    if '--verify' in opt:
        vr = json.load(open(opt['--verify'], encoding='utf-8'))
        check('V1/A2 verify PASS', bool(vr.get('pass')), ','.join(vr.get('fails', [])[:3]))
    elif '--mp4' in opt:
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,codec_type',
                            '-of', 'csv', opt['--mp4']], capture_output=True, text=True)
        check('V1 geometry+audio', '1920' in r.stdout and '1080' in r.stdout and 'audio' in r.stdout,
              r.stdout.strip().splitlines()[0][:80] if r.stdout.strip() else 'no streams')
    else:
        check('V1/A2 streams checked', False, 'no --mp4 or --verify given')

    print('\n'.join(PASS + FAIL))
    print('GATE ' + ('GREEN' if not FAIL else 'RED'))
    sys.exit(0 if not FAIL else 1)


if __name__ == '__main__':
    main()
