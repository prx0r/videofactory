#!/usr/bin/env python3
"""Independent ship validator (qprivately-type checker, anti-cheat).

Usage: python3 validate_ship.py <storyboard.json> <final.mp4> [--parts-dir D] [--out verdict.json]

Reads ONLY measured artifacts — part render_metas (hold entries),
verify.json, subs, review/approval/ears files — never storyboard estimates,
never the builder's hold simulation. Different code path from scan_holds /
gate_storyboard by construction (this module must not import them; a test
enforces it). The builder cannot grade its own homework: entries are
recomputed here (max white run incl. part-boundary merge, integrity
sum-vs-duration), and every verdict cites artifact SHAs as evidence.

Results are bool3: TRUE / FALSE / UNKNOWN (missing evidence, e.g. old
finals without part metas — UNKNOWN schedules collection, never ships).
Exit 0 iff every criterion in success.py SHIP_CRITERIA_VERSION is TRUE.
"""
import glob as _g
import json as _js
import os as _os
import re as _re
import sys as _sys

_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import factory_contract as _fc
import success as _success
import paths as _vf


def _white_runs(entries):
    """Max single white span + leading/trailing runs from ordered entries."""
    best, cur = 0.0, 0.0
    for e in entries:
        if e.get('kind') == 'white':
            cur += float(e.get('dur', 0))
            best = max(best, cur)
        else:
            cur = 0.0
    lead = 0.0
    for e in entries:
        if e.get('kind') == 'white':
            lead += float(e.get('dur', 0))
        else:
            break
    trail = 0.0
    for e in reversed(entries):
        if e.get('kind') == 'white':
            trail += float(e.get('dur', 0))
        else:
            break
    return best, lead, trail


def criterion_max_white_span(sb_path, final_mp4, parts_dir=None):
    """TRUE if no single white hold past MAX_WHITE_SPAN_S (measured).
    UNKNOWN when part metas/entries are absent (old finals)."""
    base = _os.path.basename(str(final_mp4))
    stem = base[:-len('_full.mp4')] if base.endswith('_full.mp4') else _os.path.splitext(base)[0]
    if parts_dir is None:
        parts_dir = _os.path.join(_os.path.dirname(str(final_mp4)), f'{stem}_parts')
    metas = sorted(_g.glob(_os.path.join(str(parts_dir), 'p*.render_meta.json')))
    ev = {'parts_dir': str(parts_dir), 'parts': len(metas),
          'criterion': 'ship/max-white-span-v1', 'threshold_s': _success.MAX_WHITE_SPAN_S}
    if not metas:
        return None, dict(ev, reason='no part metas beside finals (old final: re-render or file parts-proof)')
    per_part, shas = [], []
    for mp in metas:
        try:
            m = _fc.read_json(mp)
            _fc.validate_schema('render-meta', m, mp)
        except _fc.ContractError as e:
            return False, dict(ev, reason=f'unreadable/invalid part meta {mp}: {e}'[:300])
        entries = m.get('entries') or []
        if not entries:
            return None, dict(ev, reason=f'{mp} has no hold entries (built before entries landed; rebuild)')
        if len(entries) != m.get('cuts', -1):
            return False, dict(ev, reason=f'{mp}: entries {len(entries)} != cuts {m.get("cuts")}')
        if abs(sum(float(e.get('dur', 0)) for e in entries) - float(m.get('duration', 0))) > _success.ENTRIES_DURATION_TOL_S:
            return False, dict(ev, reason=f'{mp}: entries sum drifts from measured duration')
        best, lead, trail = _white_runs(entries)
        per_part.append({'part': _os.path.basename(mp), 'max_white_s': round(best, 2),
                         'sha256': _fc.sha256(mp)})
        shas.append((best, lead, trail))
    cross = 0.0
    for i in range(len(shas) - 1):
        cross = max(cross, shas[i][2] + shas[i + 1][1])
    worst = max([s[0] for s in shas] + [cross])
    ev.update(parts=per_part, max_white_span_s=round(worst, 2),
              boundary_merged_s=round(cross, 2))
    if worst > _success.MAX_WHITE_SPAN_S:
        return False, dict(ev, reason=f'max single white {worst:.0f}s > {_success.MAX_WHITE_SPAN_S:.0f}s')
    return True, ev


def criterion_geometry_proven(sb_path, final_mp4, parts_dir=None):
    """TRUE if every part meta validates AND matches current inputs (the
    geometry gate provably ran on these exact bytes)."""
    base = _os.path.basename(str(final_mp4))
    stem = base[:-len('_full.mp4')] if base.endswith('_full.mp4') else _os.path.splitext(base)[0]
    if parts_dir is None:
        parts_dir = _os.path.join(_os.path.dirname(str(final_mp4)), f'{stem}_parts')
    metas = sorted(_g.glob(_os.path.join(str(parts_dir), 'p*.render_meta.json')))
    ev = {'parts_dir': str(parts_dir), 'parts': len(metas), 'criterion': 'ship/geometry-proven-v1'}
    if not metas:
        return None, dict(ev, reason='no part metas beside finals')
    checked = []
    for mp in metas:
        video = mp[:-len('.render_meta.json')] + '.mp4'
        try:
            _fc.validate_clip_artifacts(sb_path, video)
            checked.append({'part': _os.path.basename(video), 'sha256': _fc.sha256(video)})
        except _fc.ContractError as e:
            return False, dict(ev, reason=f'{video}: {e}'[:300])
    ev['checked'] = checked
    return True, ev


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('storyboard')
    ap.add_argument('final')
    ap.add_argument('--parts-dir', default=None)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    results, evidence = {}, {}
    try:
        _fc.require_verified_video(args.storyboard, args.final)
        results['ship/verified-v1'] = True
        evidence['ship/verified-v1'] = {'video_sha256': _fc.sha256(args.final)}
    except _fc.ContractError as e:
        results['ship/verified-v1'] = False
        evidence['ship/verified-v1'] = {'reason': str(e)[:300]}
    for cid, fn in (('ship/max-white-span-v1', criterion_max_white_span),
                    ('ship/geometry-proven-v1', criterion_geometry_proven)):
        try:
            ok, ev = fn(args.storyboard, args.final, args.parts_dir)
        except _fc.ContractError as e:
            ok, ev = False, {'reason': str(e)[:300]}
        results[cid] = ok
        evidence[cid] = ev
    for cid, fn in (('ship/review-current-v1', _fc.require_current_review_pack),
                    ('ship/ears-v1', _fc.require_owner_ears),
                    ('ship/issues-clear-v1', lambda sb: _fc.require_issues_clear(sb))):
        try:
            if cid == 'ship/ears-v1':
                fn(args.storyboard, args.final)
            else:
                fn(args.storyboard)
            results[cid] = True
            evidence[cid] = {'gate': 'PASS'}
        except _fc.ContractError as e:
            results[cid] = False
            evidence[cid] = {'reason': str(e)[:300]}
    verdict = {'version': 1, 'criteria_version': _success.SHIP_CRITERIA_VERSION,
               'storyboard_sha256': _fc.sha256(args.storyboard),
               'final_sha256': _fc.sha256(args.final) if _os.path.exists(args.final) else None,
               'results': {k: (True if v is True else False if v is False else 'UNKNOWN') for k, v in results.items()},
               'evidence': evidence}
    ship = all(v is True for v in results.values())
    verdict['ship'] = ship
    out = args.out or (str(args.final) + '.ship.json')
    _js.dump(verdict, open(out, 'w'), indent=1)
    for cid in [c[0] for c in _success.CRITERIA]:
        print(f'{"PASS" if results.get(cid) is True else "UNKNOWN" if results.get(cid) is None else "FAIL"} {cid}')
    print('VALIDATE_SHIP ' + ('GREEN (ship)' if ship else 'RED (no ship)'))
    return 0 if ship else 1


if __name__ == '__main__':
    _sys.exit(main())
