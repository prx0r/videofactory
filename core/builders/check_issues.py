#!/usr/bin/env python3
"""Checker -> issues.json -> skill lookup (the issue-skill loop as code).

Usage: python3 check_issues.py <storyboard.json> [--out issues.json] [--max 60]

Runs, in order (fail-fast each, all recorded):
  bundle (validate_bundle) -> V5b/V5c data checks -> audio-complete ->
  list-geometry -> verse-gloss-missing -> verse-deva-no-english ->
  stale-verse-hold -> stack-crash -> hold-scan -> canon-shape ->
  tts-ready (last two: shiva lane only; tantrasara finished/frozen).
Emits schema-validated issues.json (issues.schema.json): one entry per
finding with kind, severity, detail, blocks, skill name, status.
Flow: run checker -> issue? look up skill in core/skills/REGISTRY.json ->
apply skill steps -> re-run checker -> green. New kind? resolve it, write
core/skills/<kind>.md + register, same commit as the fix.
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))
sys.path.insert(0, BASE)
import paths as _vf
import factory_contract as _fc


def _sha(p):
    import hashlib
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    a = sys.argv[1:]
    sb_path = a[0]
    opt = dict(zip(a[1::2], a[2::2]))
    out = opt.get('--out', os.path.splitext(sb_path)[0] + '.issues.json')
    max_hold = opt.get('--max', '60')
    try:
        unit = _fc.lane_paths(os.path.abspath(sb_path))['unit']
    except Exception:
        m = re.search(r'ch(\d+)', os.path.basename(sb_path))
        unit = (m.group(1) if m else '01').zfill(2)
    issues = []

    def add(kind, severity, detail, blocks=None, status='open'):
        issues.append({'id': f'{kind}-{len(issues) + 1}', 'kind': kind,
                       'severity': severity, 'detail': detail[:500],
                       'blocks': blocks or [], 'skill': kind, 'status': status,
                       'resolution_note': ''})

    # 1. bundle (schema + confirmed discipline + approval not required here;
    #    run_blocks adds require_approval=True at video entry)
    try:
        bundle = _fc.validate_bundle(sb_path)
        gl = bundle['glossary']
    except _fc.ContractError as e:
        msg = str(e)
        if 'empty gloss' in msg or "does not match" in msg and 'gloss' in msg:
            keys = re.findall(r'(\S+)\.gloss', msg)[:5]
            add('empty-gloss', 'needs-owner', msg, [], 'open')
        elif 'machine' in msg and 'Deva' in msg:
            keys = re.findall(r'(\S+): confirmed with', msg)[:5]
            add('machine-deva', 'needs-owner', msg, [], 'open')
        else:
            add('hold-scan-red', 'block', f'bundle: {msg}', [], 'open')
        gl = {}
        bundle = None
    # 2. V5b/V5c direct (names keys even when schema already failed)
    if bundle is not None:
        nogloss = [k for k, v in gl.items() if isinstance(v, dict)
                   and v.get('status') == 'confirmed' and not (v.get('gloss') or '').strip()]
        if nogloss:
            add('empty-gloss', 'needs-owner',
                f'{len(nogloss)} confirmed-with-empty-gloss: {nogloss[:5]} — fill or proposed-flip', [], 'open')
        machine = [k for k, v in gl.items() if isinstance(v, dict)
                   and v.get('status') == 'confirmed' and v.get('deva_status') in ('machine', 'machine-lossy')]
        if machine:
            add('machine-deva', 'needs-owner',
                f'{len(machine)} machine-Deva confirmed: {machine[:5]} — owner Deva pass required (M15/M23)', [], 'open')
    # 3-4. audio-complete + list-geometry need a valid bundle first;
    # without it they just repeat the bundle error — skip and let the
    # bundle issue + scan carry the unit.
    bundle_ok = bundle is not None
    if bundle_ok:
        try:
            _fc.require_audio_complete(sb_path)
        except _fc.ContractError as e:
            msg = str(e)
            bids = re.findall(r'b\d+', msg)[:5]
            add('missing-audio', 'block', msg, bids, 'open')
        try:
            _fc.require_list_geometry(sb_path)
        except _fc.ContractError as e:
            msg = str(e)
            add('list-geometry', 'needs-owner', msg, [], 'open')
    # 5. verse-gloss coverage: multi-line verses without a mined entry
    # render Devanagari-only (honest, but the owner asked English under all
    # Devanagari — file the gloss from T1/L3, then bulk-confirm).
    try:
        _sb = json.load(open(sb_path, encoding='utf-8'))
        _ml = [b for b in _sb['blocks'] if b.get('type') == 'verse' and len(b.get('text', '').split()) > 3]
        if _ml:
            import sys as _s2
            _s2.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import holds as _H
            _vgp = None
            try:
                _vgp = _H.lane_for(os.path.abspath(sb_path)).get('verse')
            except Exception:
                pass
            _vg = json.load(open(_vgp, encoding='utf-8')) if _vgp and os.path.exists(_vgp) else {}
            _have = set()
            for _ref, _e in _vg.items():
                if isinstance(_e, dict):
                    for _bid in _e.get('bids', []):
                        _have.add(_bid)
            # b2 is the chapter-name chant in tantrasara chapters (title
            # line, not a T1 root verse) — never needs verse_gloss. Other
            # lanes have no such convention (shiva b2s are real chants).
            _lane = 'tantrasara'
            try:
                _lane = _H.lane_for(os.path.abspath(sb_path)).get('lane', 'tantrasara')
            except Exception:
                pass
            _miss = [b['id'] for b in _ml if b['id'] not in _have
                     and not (b['id'] == 'b2' and _lane == 'tantrasara')]
            if _miss:
                add('verse-gloss-missing', 'needs-owner',
                    f'{len(_miss)}/{len(_ml)} multi-line verses without verse_gloss (Devanagari-only cards): { _miss[:6]} — mine from T1/L3 then bulk-confirm', _miss[:6], 'open')
    except Exception:
        pass
    # 5b. verse-deva-no-english (renderer-identical): verse cards that will
    # ship Devanagari with no English underneath. Superset of step 5 with
    # the renderer's own decision rule (confirmed verse_gloss literal/final
    # via verse_match_key, else confirmed term layers for single chants):
    # covers proposed-only, stale bids, label-polluted keys and split-off
    # roman halves — every shape in core/skills/verse-deva-no-english.md.
    # 5c. stale-verse-hold: one Sanskrit verse scattered over several blocks
    # (Deva + roman half + granny/man IAST tail), so cards show regenerated
    # or older Devanagari and the following narration holds a stale half-card
    # instead of the verse. Structural (no timing estimates); one issue per
    # span with the reblock prescription in core/skills/stale-verse-hold.md.
    # Both share check_verse_cards.check so CLI and checker always agree.
    try:
        import check_verse_cards as _vc
        _res = _vc.check(sb_path)
        _noeng = _res['no_english']
        if _noeng:
            _bids = [f['bid'] for f in _noeng]
            add('verse-deva-no-english', 'needs-owner',
                f'{len(_bids)} verse cards ship Devanagari with no English underneath: {_bids[:6]}'
                f' — mine verse_gloss from T1/L3 (or confirm proposed) then bulk-confirm; '
                f'split halves need reblocking first (see stale-verse-hold)', _bids[:6], 'open')
        for _sp in _res['spans']:
            add('stale-verse-hold', 'needs-owner', _sp['detail'][:500], _sp['bids'][:6], 'open')
    except Exception:
        pass
    # 5d. stack-crash: RETIRED 2026-11-06. The renderer now fires exactly
    # ONE cue per block (matching the documented rule the gates always
    # modelled), so same-block multi-cue stack runs cannot form; the entry
    # gate and the renderer agree by construction. The predictor stays in
    # the tree (check_stacks.py) as a forensic tool for old builds only —
    # it is not part of the runtime work list.
    # 6. hold-scan (estimates; verse-term fix applied in scan)
    scan = os.path.join(BASE, 'scan_holds.py')
    r = subprocess.run([sys.executable, scan, sb_path, '--max', max_hold],
                       capture_output=True, text=True)
    for line in (r.stdout or '').splitlines():
        if line.startswith('FAIL hold'):
            kind = 'stuck-term' if 'STUCK_TERM' in line else 'white-gap'
            bids = re.findall(r'b\d+', line)[:3]
            sev = 'needs-draw'
            add(kind, sev, line, bids, 'open')
    if r.returncode and not any(i['kind'] in ('white-gap', 'stuck-term') for i in issues):
        add('hold-scan-red', 'needs-owner', (r.stdout or '')[-500:], [], 'open')
    # 7-8. script canon (shiva only — tantrasara storyboards are finished
    # and frozen; check_canon.py no-ops on other lanes by construction).
    # canon-shape: unit skeleton vs the lane canon (order/presence of
    # beats). tts-ready: mechanical delivery defects (leading junk,
    # lone diacritics, embedded labels, URLs/markdown/tails/read-more;
    # Next: trailers and enumeration patter explicitly excluded).
    try:
        import check_canon as _vc2
        _res2 = _vc2.check(sb_path)
        for _f in _res2.get('shapes', []):
            add('canon-shape', 'needs-owner', _f['reason'][:500], [_f['bid']], 'open')
        for _f in _res2.get('hygiene', []):
            add('tts-ready', 'needs-owner', _f['reason'][:500], [_f['bid']], 'open')
    except Exception:
        pass

    doc = {'version': 1, 'unit': unit, 'storyboard_sha256': _sha(sb_path), 'issues': issues}
    # owner waivers: sibling <stem>.waivers.json lists issue ids the owner
    # accepts (draw filed elsewhere, golden blessing, risk taken). Waived
    # issues stay visible but no longer gate.
    wpath = os.path.join(os.path.dirname(os.path.abspath(out)),
                         os.path.basename(out).replace('.issues.json', '.waivers.json'))
    if os.path.exists(wpath):
        try:
            wv = json.load(open(wpath, encoding='utf-8'))
            waived = set(wv.get('waived', [])) if isinstance(wv, dict) else set()
            for i in doc['issues']:
                if i['id'] in waived and i['status'] == 'open':
                    i['status'] = 'waived-owner'
                    i['resolution_note'] = (wv.get('reason', '') + f" (waived {wv.get('date', '')})").strip()
        except (OSError, ValueError) as e:
            print(f'WARNING ignoring unreadable waivers file {wpath}: {e}')
    _fc.validate_schema('issues', doc, 'issues doc')
    json.dump(doc, open(out, 'w'), indent=1)
    # skill lookup printout: the loop made visible
    reg = json.load(open(os.path.join(BASE, '..', 'skills', 'REGISTRY.json')))
    print(f'unit {unit}: {len(issues)} issues -> {out}')
    for i in issues:
        sk = reg['skills'].get(i["kind"], {})
        print(f'  [{i["severity"]}] {i["id"]} ({i["kind"]}): {i["detail"][:120]}')
        print(f'    skill: core/skills/{sk.get("file", i["kind"] + ".md")} auto={sk.get("auto")} needs_owner={sk.get("needs_owner")}')
    print('ISSUES ' + ('RED' if issues else 'GREEN'))
    sys.exit(0)


if __name__ == '__main__':
    main()
