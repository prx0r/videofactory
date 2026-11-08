#!/usr/bin/env python3
"""Per-video catalog: title + thumbnail + state for every unit in a lane.

Usage: python3 catalog.py <project> [--out catalog.json] [--json]

Derived artifact (regenerable, read-only inputs): storyboard + approval +
final + issues + ship verdict per unit, plus the display title (lane
convention from chapter source) and the thumbnail (per-unit stem art or
series fallback). Owners drop per-video art at assets/thumbnail/<stem>.png
and it appears here on the next run; nothing else changes.

Exit 0 with the catalog on stdout (or --out path).
"""
import glob as _g
import hashlib as _h
import json as _j
import os as _o
import re as _re
import sys as _s

_sys_path = _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..', 'contract')
if _sys_path not in _s.path:
    _s.path.insert(0, _sys_path)
import paths as _vf

_sys_b = _o.path.dirname(_o.path.abspath(__file__))
if _sys_b not in _s.path:
    _s.path.insert(0, _sys_b)
_sys_c = _o.path.normpath(_o.path.join(_sys_b, '..'))
if _sys_c not in _s.path:
    _s.path.insert(0, _sys_c)
import lane_api as _api


def _unit_ids(cfg):
    target = int(cfg.get('unit_target', 0) or 0)
    scheme = cfg.get('unit_scheme', 'chNN')
    if scheme == 'chNN':
        return [f'{i:02d}' for i in range(1, (target or 22) + 1)]
    if scheme == 'sNN':
        return [f's{i:02d}' for i in range(0, (target or 78))]
    if scheme == 'nNN':
        return [f'n{i:02d}' for i in range(1, (target or 10) + 1)]
    if scheme == 'pNN':
        return [f'p{i:02d}' for i in range(1, (target or 7) + 1)]
    return []


def _chapter_title(repo, lane, unit, mod):
    """Display title from chapter source (lane convention, read-only)."""
    digits = _re.sub(r'\D', '', unit)
    cands = []
    if lane in ('nibbana',):
        cands = [_o.path.join(repo, 'chapters', f'n{digits}.md')]
    elif lane in ('paramarthasara',):
        cands = [_o.path.join(repo, 'chapters', f'p{digits}.md')]
    elif lane in ('shiva-sutras', 'shiva'):
        cands = [_o.path.join(repo, 'shiva', 'chapters', f's{digits}.md')]
    else:
        cands = [_o.path.join(repo, 'chapters', f'ch{digits}.md')]
    for path in cands:
        try:
            text = open(path, encoding='utf-8').read()
        except OSError:
            continue
        if lane == 'nibbana':
            for pat in (r'^## (.+)$', r'^### (.+)$'):
                m = _re.search(pat, text, _re.M)
                if m:
                    return m.group(1)[:120]
            return f'Chapter {digits}'
        elif lane == 'paramarthasara':
            m = _re.search(r'^### (Part .+)$', text, _re.M)
            if m:
                return m.group(1)[:120]
        else:
            m = _re.search(r'^# (.+)$', text, _re.M)
            if m:
                return m.group(1)[:120]
    return f'{lane} {unit}'


def _thumbnail(assets_dir, stems):
    """Per-unit stem art, else series fallback, else None."""
    for stem in stems:
        hit = _o.path.join(assets_dir, f'{stem}.png')
        if _o.path.isfile(hit):
            return {'file': hit, 'kind': 'unit'}
    series = _o.path.join(assets_dir, 'series.png')
    if _o.path.isfile(series):
        return {'file': series, 'kind': 'series-fallback'}
    return {'file': None, 'kind': 'none'}


def _row(project, mod, env, unit):
    repo, renders = env['VF_REPO'], env['VF_RENDERS']
    try:
        sb, stem, _, _ = _resolve(project, mod, env, repo, unit)
    except (FileNotFoundError, ValueError):
        return {'unit': unit, 'stage': 'missing-storyboard'}
    stems = _stem_aliases(stem)
    appr = []
    for s in stems:
        appr += _g.glob(_o.path.join(repo, '**', f'approved_{s}.json'), recursive=True)
    final = next((_o.path.join(renders, 'finals', f'{s}_full.mp4') for s in stems
                  if _o.path.exists(_o.path.join(renders, 'finals', f'{s}_full.mp4'))), None)
    open_n, waived_n = 0, 0
    for s in stems:
        issues_p = _o.path.join(renders, 'issues', f'{s}.issues.json')
        try:
            doc = _j.load(open(issues_p, encoding='utf-8'))
            for i in doc.get('issues', []):
                if i.get('status') == 'open':
                    open_n += 1
                elif str(i.get('status', '')).startswith('waived'):
                    waived_n += 1
            break
        except (OSError, ValueError):
            continue
    ship = None
    if final:
        try:
            ship = _j.load(open(final + '.ship.json', encoding='utf-8')).get('ship', None)
        except (OSError, ValueError):
            ship = None
    assets = _o.path.join(repo, mod.paths(repo, _re.sub(r'\D', '', unit).zfill(2)).get('assets', 'assets') if hasattr(mod, 'paths') else 'assets')
    try:
        assets = mod.paths(repo, _re.sub(r'\D', '', unit).zfill(2))['assets']
    except (KeyError, AttributeError, TypeError, ValueError):
        pass
    thumb = _thumbnail(assets, stems)
    return {
        'unit': unit, 'stem': stem,
        'title': _chapter_title(repo, env.get('VF_SERIES', project), unit, mod),
        'thumbnail': thumb['file'], 'thumbnail_kind': thumb['kind'],
        'storyboard_sha256': _h.sha256(open(sb, 'rb').read()).hexdigest()[:16],
        'approval': bool(appr),
        'stage': 'video-needs-review' if (final and appr) else ('approved-ready' if appr else 'needs-review'),
        'final_bytes': _o.path.getsize(final) if final else 0,
        'issues_open': open_n, 'issues_waived': waived_n,
        'ship': ship,
    }


def _stem_aliases(stem):
    m = _re.match(r'^([a-zA-Z_]+)(\d+)$', stem)
    if not m:
        return [stem]
    prefix, digits = m.group(1), m.group(2)
    return list(dict.fromkeys([stem, f'{prefix}{int(digits):02d}', f'{prefix}{int(digits)}']))


def _resolve(project, mod, env, repo, unit):
    digits = _re.sub(r'\D', '', unit).zfill(2)
    cands = []
    for cand in dict.fromkeys([unit, digits]):
        cands += mod.paths(repo, cand).get('storyboards', [])
    sb = next((c for c in cands if _o.path.exists(c)), None)
    if sb is None:
        raise FileNotFoundError(f"unit '{unit}' not found in lane '{project}'")
    base = _o.path.basename(sb)
    if base.startswith('storyboard_'):
        base = base[len('storyboard_'):]
    return sb, _o.path.splitext(base)[0], env, None


def main():
    args = [a for a in _s.argv[1:] if not a.startswith('--')]
    if not args:
        print('usage: catalog.py <project> [--out catalog.json] [--json]')
        return 2
    project = args[0]
    _vf.apply_series(project)
    env = {'VF_REPO': _vf.repo_root(), 'VF_RENDERS': _vf.renders_root(),
           'VF_SERIES': _vf.series_name()}
    cfg = _vf._series_cfg()
    mod = _api.load_lane(project)
    rows = [_row(project, mod, env, u) for u in _unit_ids(cfg)]
    doc = {'project': project, 'units': len(rows), 'rows': rows}
    if '--out' in _s.argv:
        out = _s.argv[_s.argv.index('--out') + 1]
        _j.dump(doc, open(out, 'w', encoding='utf-8'), indent=1)
        print(f'catalog: {len(rows)} units -> {out}')
    else:
        print(_j.dumps(doc, indent=1)[:4000])
    return 0


if __name__ == '__main__':
    _s.exit(main())
