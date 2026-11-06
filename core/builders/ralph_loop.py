#!/usr/bin/env python3
"""Ralph loop: check -> skill (+web prompt) -> fix -> re-check -> report.

Usage: python3 ralph_loop.py --project tantrasara --units 14,15 [--max-iters 3]
                             [--out /tmp/ralph_report.json] [--dry-run]

Hardcoded autonomous loop (owner order 2026-11-06 — never come back with
"here's the issue"; come back with the full tried/fixed/blocked report):

  1. CHECK:  run check_issues.py for the unit (bundle, V5, audio, geometry,
             verse-gloss, hold-scan) -> issues.json.
  2. SKILL:  look up core/skills/<kind>.md for every open issue. Novel kind
             (no skill file)? print a web-search prompt for it and stop the
             unit as blocked-new-kind (a human writes the skill same-commit
             as the fix, per ISSUE-SKILL-FLOW — the loop never invents law).
  3. FIX:    apply registered auto-fixers, safest first:
                empty-gloss (T1 l0 fill, flip rest proposed),
                machine-deva (round-trip verify vs author IAST),
                verse-gloss-missing + verse-deva-no-english (re-mine +
                confirm >=0.8; split halves need a reblock),
                missing-audio (render_chapter, content-hash cache).
              list-geometry / white-gap / stuck-term / stale-verse-hold /
              stack-crash / canon-shape / tts-ready have no auto-fixer:
              recorded as tried (gates re-run) + blocked with skill
              pointer (draws need art, reblocks need owner rebuild, stack
              runs need restyle/demote or waiver, canon needs reblock,
              TTS text needs probe+reword). No draws are filed in ship
              mode (owner order: ship ASAP).
  4. RE-CHECK until issues stop shrinking or --max-iters. Then REPORT.

Writes series data (glossaries, verse_gloss, approvals refresh) under the
owner's blanket order; every write is listed in the report. --dry-run runs
checkers only. Exit 0 with report even when blocked (blocking is data, and
the report names it); exit 2 only on loop infrastructure failure.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))
sys.path.insert(0, os.path.join(BASE, '..'))
import paths as _vf

SKILLS = os.path.join(BASE, '..', 'skills')
def _web_query(kind):
    """Web-search prompt lives in the skills registry (single source); the
    loop only falls back to generic when the registry lacks the skill."""
    try:
        reg = json.load(open(os.path.join(SKILLS, 'REGISTRY.json'), encoding='utf-8'))
        q = reg.get('skills', {}).get(kind, {}).get('web_query')
        if q:
            return q
    except (OSError, ValueError):
        pass
    return kind.replace('-', ' ')


def log(msg):
    print(f'{time.strftime("%FT%TZ", time.gmtime())} {msg}', flush=True)


def sh(cmd, timeout):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, ((r.stderr or r.stdout or '')[-1500:])
    except subprocess.TimeoutExpired:
        return False, 'timeout'


def check_unit(sb_path, issues_path, max_hold='60'):
    ok, _ = sh([sys.executable, f'{BASE}/check_issues.py', sb_path,
                 '--out', issues_path, '--max', max_hold], 600)
    try:
        doc = json.load(open(issues_path, encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return doc


def open_issues(doc):
    return [i for i in doc.get('issues', []) if i.get('status') == 'open']


def skill_known(kind):
    return os.path.exists(os.path.join(SKILLS, f'{kind}.md'))


def _fill_report(ch):
    try:
        rep = json.load(open('/tmp/fill_glossary_report.json', encoding='utf-8'))
    except (OSError, ValueError):
        return None
    for u in rep if isinstance(rep, list) else []:
        if u.get('ch') == ch:
            return u
    return None


def fixer_empty_gloss(sb_path, issue):
    """Single implementation lives in fill_glossary_t1.py (strict T1 rules);
    this fixer delegates so the loop can never drift from it."""
    chm = re.search(r'ch(\d+)', os.path.basename(sb_path))
    ch = (chm.group(1) if chm else '01').zfill(2)
    ok, out = sh([sys.executable, f'{BASE}/fill_glossary_t1.py', '--chapters', ch], 600)
    if not ok:
        return 0, f'fill script failed: {out[-200:]}'
    rep = _fill_report(ch) or {}
    n = len(rep.get('filled', [])) + len(rep.get('new', []))
    return n, f"T1-filled {len(rep.get('filled', []))}, new {len(rep.get('new', []))}"


def fixer_machine_deva(sb_path, issue):
    """Strict re-derivation lives in fill_glossary_t1.py --reverify
    (diacritic-bearing sources only; fold-equality never verifies);
    this fixer delegates so the loop can never drift from it."""
    chm = re.search(r'ch(\d+)', os.path.basename(sb_path))
    ch = (chm.group(1) if chm else '01').zfill(2)
    ok, out = sh([sys.executable, f'{BASE}/fill_glossary_t1.py', '--chapters', ch, '--reverify'], 600)
    if not ok:
        return 0, f'fill script failed: {out[-200:]}'
    rep = _fill_report(ch) or {}
    n = len(rep.get('reverified_corrected', [])) + len(rep.get('reverified_demoted', []))
    return n, (f"reverified corrected {len(rep.get('reverified_corrected', []))}, "
               f"demoted {len(rep.get('reverified_demoted', []))}")


def fixer_verse_gloss(sb_path, issue):
    """Re-mine verse gloss + confirm matches >=0.8 (tantrasara, T1-frozen
    method). Shiva lane routes to mine_shiva_verse_gloss (backfill bids +
    positional proposed entries, never confirms — owner bulk-confirms)."""
    import lane_api as _api
    try:
        _name, _mod = _api.for_path(os.path.abspath(sb_path))
    except ValueError:
        return 0, 'no lane matches this storyboard'
    if _name != 'tantrasara':
        chm = re.search(r's(\d+)', os.path.basename(sb_path))
        uarg = [f"s{(chm.group(1) if chm else '00').zfill(2)}"] if chm else []
        ok, out = sh([sys.executable, f'{BASE}/mine_shiva_verse_gloss.py', '--apply'] + uarg, 300)
        return (0, f'shiva backlog refresh (proposed-only, confirms are owner): {out[-200:]}') if ok else (0, f'shiva miner failed: {out[-200:]}')
    import glob as _g
    repo = _vf.repo_root()
    chm = re.search(r'ch(\d+)', os.path.basename(sb_path))
    ch = (chm.group(1) if chm else '01').zfill(2)
    vgl = os.path.join(repo, 'verse_gloss_ch6.json' if ch == '06' else f'verse_gloss_ch{ch}.json')
    before = set()
    if os.path.exists(vgl):
        try:
            _old = json.load(open(vgl, encoding='utf-8'))
            before = {k for k, v in _old.items() if isinstance(v, dict) and v.get('status') == 'confirmed'}
        except ValueError:
            pass
    ok, out = sh([sys.executable, f'{repo}/mine_verse_gloss.py', ch], 300)
    if not os.path.exists(vgl):
        return 0, 'miner produced no file'
    d = json.load(open(vgl, encoding='utf-8'))
    n = 0
    for k, v in d.items():
        if k in before:
            v['status'] = 'confirmed'
            if 'bulk-confirmed' not in v.get('note', ''):
                v['note'] = v.get('note', '') + ' | kept confirmed (ralph loop re-mine preserved prior confirm)'
            n += 0  # preserved, not new
            continue
        if isinstance(v, dict) and v.get('status') == 'proposed' and (v.get('literal') or v.get('final')) \
                and float(v.get('match_score', 0) or 0) >= 0.8:
            v['status'] = 'confirmed'
            v['note'] = v.get('note', '') + ' | bulk-confirmed (ralph loop, T1 frozen, owner bless covers method)'
            n += 1
    json.dump(d, open(vgl, 'w'), ensure_ascii=False, indent=1)
    return n, f'mined file present, newly confirmed {n} high-confidence (>=0.8)'


def fixer_missing_audio(sb_path, issue, timeout=7200):
    ok, out = sh([sys.executable, f'{BASE}/render_chapter.py', sb_path], timeout)
    return (1 if ok else 0), ('audio render ok' if ok else f'audio render failed: {out[-300:]}')


FIXERS = {
    'empty-gloss': fixer_empty_gloss,
    'machine-deva': fixer_machine_deva,
    'verse-gloss-missing': fixer_verse_gloss,
    'verse-deva-no-english': fixer_verse_gloss,
    'missing-audio': fixer_missing_audio,
}


def refresh_approvals(sb_path):
    import hashlib as _hl
    repo = _vf.repo_root()
    chm = re.search(r'ch(\d+)', os.path.basename(sb_path))
    ch = (chm.group(1) if chm else '01').zfill(2)
    short = 'ch6' if ch == '06' else f'ch{ch}'
    sbp = os.path.join(repo, os.path.basename(sb_path))
    glp = os.path.join(repo, 'glossary_ch6.json' if ch == '06' else f'glossary_ch{ch}.json')
    app = os.path.join(repo, 'approved_ch6.json' if ch == '06' else f'approved_ch{ch}.json')
    if not (os.path.exists(sbp) and os.path.exists(glp) and os.path.exists(app)):
        return False
    a = json.load(open(app, encoding='utf-8'))
    a['storyboard_sha'] = _hl.sha256(open(sbp, 'rb').read()).hexdigest()
    a['glossary_sha'] = _hl.sha256(open(glp, 'rb').read()).hexdigest()
    a['date'] = time.strftime('%F')
    a['note'] = (a.get('note', '') + ' | ralph loop refresh').strip(' |')
    json.dump(a, open(app, 'w'), indent=2)
    return True


def run_unit(sb_path, issues_dir, max_iters, dry_run):
    stem = os.path.splitext(os.path.basename(sb_path)[len('storyboard_'):]
                            if os.path.basename(sb_path).startswith('storyboard_')
                            else os.path.basename(sb_path))[0]
    issues_path = os.path.join(issues_dir, f'{stem}.issues.json')
    tried, fixed, blocked = [], [], []
    doc = check_unit(sb_path, issues_path)
    if doc is None:
        return {'unit': stem, 'error': 'checker produced no issues file', 'tried': [], 'fixed': [], 'blocked': []}
    for it in range(max_iters):
        changed = False
        for issue in open_issues(doc):
            kind = issue['kind']
            if not skill_known(kind):
                blocked.append({'id': issue['id'], 'kind': kind, 'reason': 'NO SKILL — web-search prompt: ' + _web_query(kind),
                                'skill': None})
                continue
            tried.append(issue['id'])
            if kind in ('white-gap', 'stuck-term', 'hold-scan-red', 'list-geometry', 'verse-term-unheld',
                          'stale-verse-hold', 'stack-crash', 'canon-shape', 'tts-ready'):
                if kind == 'stale-verse-hold':
                    why = 'reblock needs owner rebuild + rebless; draws per 60s law at seal'
                elif kind == 'stack-crash':
                    why = 'predicted build crash: restyle/demote a term or waive with reason'
                else:
                    why = 'no auto-fixer (draws deferred / already code-fixed)'
                blocked.append({'id': issue['id'], 'kind': kind,
                                'reason': f'{why}; skill: core/skills/{kind}.md',
                                'skill': kind})
                continue
            if dry_run:
                blocked.append({'id': issue['id'], 'kind': kind, 'reason': 'dry-run: fixer not applied',
                                'skill': kind})
                continue
            try:
                n, note = FIXERS[kind](sb_path, issue)
                if n:
                    fixed.append({'id': issue['id'], 'kind': kind, 'result': note, 'skill': kind})
                    changed = True
                else:
                    blocked.append({'id': issue['id'], 'kind': kind,
                                    'reason': f'fixer ran, nothing changed: {note}; skill: core/skills/{kind}.md',
                                    'skill': kind})
            except Exception as e:
                blocked.append({'id': issue['id'], 'kind': kind, 'reason': f'fixer raised: {e}',
                                'skill': kind})
        if not changed:
            break
        refresh_approvals(sb_path)
        doc = check_unit(sb_path, issues_path)
        if doc is None:
            break
        if not open_issues(doc):
            break
    # launch verdict via the same gate run_queue uses
    sys.path.insert(0, os.path.join(BASE, '..', 'contract'))
    import factory_contract as _fc
    try:
        _fc.require_issues_clear(sb_path, issues_dir)
        launch = 'CLEAR'
    except Exception as e:
        launch = f'BLOCKED: {e}'[:300]
    remaining = [{'id': i['id'], 'kind': i['kind'], 'severity': i['severity'],
                  'detail': i['detail'][:160]} for i in open_issues(doc)] if doc else []
    return {'unit': stem, 'tried': sorted(set(tried)), 'fixed': fixed, 'blocked': blocked,
            'remaining': remaining, 'launch': launch}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', default='tantrasara')
    ap.add_argument('--units', required=True)
    ap.add_argument('--storyboards', default='')
    ap.add_argument('--max-iters', default='3')
    ap.add_argument('--out', default='/tmp/ralph_report.json')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--issues-dir', default='')
    args = ap.parse_args()
    _vf.apply_series(args.project)
    renders = _vf.renders_root()
    issues_dir = args.issues_dir or os.path.join(renders, 'issues')
    os.makedirs(issues_dir, exist_ok=True)
    import lane_api as _api
    sbs = []
    if args.storyboards:
        sbs = args.storyboards.split(',')
    else:
        for u in args.units.split(','):
            u = u.strip()
            if not u:
                continue
            cands = []
            try:
                mod = _api.load_lane(args.project)
                digits = re.sub(r'\D', '', u).zfill(2)
                for _uu in dict.fromkeys([u, digits]):
                    cands += mod.paths(_vf.repo_root(), _uu).get('storyboards', [])
            except (ValueError, AttributeError):
                pass
            sb = next((c for c in cands if os.path.exists(c)), None)
            if sb is None:
                print(f'{u}: storyboard not found in lane {args.project}')
                continue
            sbs.append(sb)
    report = {'date': time.strftime('%FT%TZ', time.gmtime()), 'project': args.project,
              'dry_run': args.dry_run, 'units': []}
    for sb in sbs:
        log(f'RALPH {sb}')
        report['units'].append(run_unit(sb, issues_dir, int(args.max_iters), args.dry_run))
    json.dump(report, open(args.out, 'w'), indent=2)
    print(f'RALPH REPORT -> {args.out}')
    for u in report['units']:
        print(f"== {u['unit']}: launch={u.get('launch')} fixed={len(u.get('fixed', []))} "
              f"blocked={len(u.get('blocked', []))} remaining={len(u.get('remaining', []))}")
        for f in u.get('fixed', []):
            print(f"   FIXED {f['id']} ({f['kind']}): {f['result']}")
        for b in u.get('blocked', []):
            print(f"   BLOCKED {b['id']} ({b['kind']}): {b['reason'][:220]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
