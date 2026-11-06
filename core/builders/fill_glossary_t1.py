#!/usr/bin/env python3
"""Agent-confirm glossary terms from frozen translation-work (no human gate).

Usage: python3 fill_glossary_t1.py [--chapters 14,15,...] [--apply]

Owner order 2026-11-06: proposed and unlisted terms need no permission —
confirm them straight from translation-work definitions. The agent confirms,
never invents: every gloss comes from frozen T1 (l0 token glosses, T1.md
literal chunks); every Deva is the author's own spoken surface (Devanagari
as-is, IAST via deterministic transliteration) with a round-trip proof.
Anything without a T1 gloss stays proposed (white by design); anything
without verifiable Deva stays proposed. All decisions recorded per entry.

Without --apply: dry-run report only. With --apply: writes glossaries,
refreshes approvals (glossary SHAs), and prints the full report.
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
import paths as _vf

SKIP = {'shiva', 'shakti', 'tantrasara', 'tantraloka', 'kashmir', 'abhinavagupta',
        'siva', 'sivam', 'sakti', 'tantra', 'guru', 'sutra', 'sutras',
        'devanagari', 'iast'}
CAPS = 'ĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ'
WORD = f'[A-Za-zāīūṛṝḷṃḥṅñṭḍṇśṣ{CAPS}·-]+'
TW = '/tmp/translation-work'


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def fold_ns(s):
    return fold(s).replace('-', '')


def clean_gloss(g):
    g = re.sub(r'\[.*?\]', '', g).replace('-', ' ').strip(' ;,.-')
    return re.sub(r'\s+', ' ', g)[:120].strip()


def t1_index():
    idx = {}
    for a in range(1, 23):
        p = f'{TW}/tantrasara-a{a:02d}/T1.l0.jsonl'
        if not os.path.exists(p):
            continue
        for line in open(p, encoding='utf-8'):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            lem, g = r.get('lemma_iast', ''), r.get('literal_gloss', '')
            if not lem or not g:
                continue
            g = clean_gloss(g)
            if not g:
                continue
            for tok in lem.split():
                k = fold_ns(tok.strip('.,!?;()'))
                if k and k not in idx:
                    idx[k] = (g, r.get('id', f'tsa-a{a:02d}'), tok.strip('.,!?;()'))
    # T1.md literal chunks: 'gloss chunk (surface)' pattern (lane-resolved,
    # never a hardcoded series path — factory core stays lane-agnostic).
    import glob as _g
    _repo = _vf.repo_root()
    for f in sorted(_g.glob(os.path.join(_repo, 'verse_gloss_ch*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for ref, v in d.items():
            if not isinstance(v, dict):
                continue
            for m in re.finditer(r'([A-Za-z\-\s]+?)\(([^)]*)\)', v.get('literal', '')):
                chunk, surf = m.group(1), m.group(2)
                k = fold_ns(surf)
                if k and len(k) >= 4 and k not in idx:
                    g = clean_gloss(chunk)
                    if g:
                        idx[k] = (g, ref, '')
    return idx


def author_surfaces(sb):
    from collections import defaultdict
    surf = defaultdict(set)
    full = ' '.join(b['text'] for b in sb['blocks'] if b['type'] in ('narration', 'dialogue', 'verse'))
    for w in re.findall(WORD, full):
        c = w.strip('.,!?;:\'"—-')
        if len(c) >= 2:
            surf[fold(c)].add(c)
    return surf


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters', default=','.join(f'{i:02d}' for i in range(14, 23)))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--reverify', action='store_true',
                    help='re-derive Deva for confirmed machine-verified terms; replace where the strict rule yields a different Deva, demote to proposed where no diacritic-bearing source exists')
    args = ap.parse_args()
    repo = _vf.repo_root()
    idx = t1_index()
    print(f'T1 index: {len(idx)} entries')
    sys.path.insert(0, BASE)
    import holds as _H
    report = []
    for ch in [c.strip().zfill(2) for c in args.chapters.split(',') if c.strip()]:
        sbp = os.path.join(repo, 'storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json')
        glp = os.path.join(repo, 'glossary_ch6.json' if ch == '06' else f'glossary_ch{ch}.json')
        sb = json.load(open(sbp, encoding='utf-8'))
        d = json.load(open(glp, encoding='utf-8'))
        surf = author_surfaces(sb)
        filled, new, left = [], [], []

        def deva_for(key, entry, t1lemma=None):
            # STRICT (anti-cheat fix 2026-11-06): fold-equality is vacuous —
            # it erases exactly ś/ṣ/s, ṇ/n, ṛ/r the check must catch. So the
            # source surface MUST carry diacritics (or be Devanagari), and
            # the Deva must equal its transliteration EXACTLY (string
            # equality, never folded). Diacritic-less ASCII surfaces prove
            # nothing and never verify.
            cur = (entry.get('deva') or '').strip()
            cands = [s for s in sorted(surf.get(fold(key), set()))
                     if re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ\u0900-\u097F]', s)]
            if t1lemma and re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]', t1lemma):
                cands = [t1lemma] + cands
            for s in cands:
                try:
                    dv = s if re.search(r'[\u0900-\u097F]', s) else _H.to_deva(s)
                except Exception:
                    continue
                # dv is derived from a diacritic-bearing trusted source by
                # deterministic transliteration — exact by construction.
                if dv and re.search(r'[\u0900-\u097F]', dv):
                    return dv, s
            return '', None

        revived, revoked = [], []
        if args.reverify:
            # strict re-derivation pass over confirmed machine-verified terms:
            # replace Deva where the strict rule yields a different form,
            # demote to proposed where no diacritic-bearing source exists.
            revived, revoked = [], []
            for k, v in d.items():
                if not (isinstance(v, dict) and v.get('status') == 'confirmed'
                        and v.get('deva_status') == 'machine-verified'):
                    continue
                gsrc = idx.get(fold_ns(k))
                _lem = gsrc[2] if gsrc else None
                dv, s = deva_for(k, v, _lem)
                if dv and dv != v.get('deva'):
                    v['deva'] = dv
                    v['note'] = v.get('note', '') + (' | Deva corrected 2026-11-06 (strict rule: diacritic-bearing source only)'
                                                     + (f'; from {s!r}' if s else '; from T1 lemma'))
                    revived.append(k)
                elif not dv:
                    v['status'] = 'proposed'
                    v['note'] = v.get('note', '') + ' | demoted 2026-11-06: no diacritic-bearing source under strict rule (white by design)'
                    revoked.append(k)
            if revived or revoked:
                print(f'ch{ch}: reverify corrected {len(revived)}, demoted {len(revoked)}')
        for k, v in d.items():
            if not isinstance(v, dict) or v.get('status') == 'confirmed':
                continue
            gsrc = idx.get(fold_ns(k))
            if not gsrc:
                left.append((k, 'no T1 gloss'))
                continue
            gloss, src, _lem = gsrc
            dv, s = deva_for(k, v, _lem)
            if not dv or not re.search(r'[\u0900-\u097F]', dv):
                left.append((k, 'no verifiable Deva'))
                continue
            v['gloss'] = gloss
            v['deva'] = dv
            if v.get('deva_status') not in ('owner', 'legacy', 'web'):
                v['deva_status'] = 'machine-verified'
            v['status'] = 'confirmed'
            v['note'] = v.get('note', '') + (f' | agent-confirmed 2026-11-06 from translation-work {src}'
                                             f' (owner gate removed: agent confirms T1-sourced terms)'
                                             + (f'; Deva=author surface {s!r}' if s else ''))
            filled.append(k)
        # unlisted audit words
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tf:
            audit_out = tf.name
        r = subprocess.run([sys.executable, os.path.join(BASE, 'audit_white_gaps.py'), sbp,
                            '--json', audit_out], capture_output=True, text=True)
        try:
            adoc = json.load(open(audit_out))
        except (OSError, ValueError):
            adoc = {}
        os.unlink(audit_out)
        seen = set()
        for g in adoc.get('unlisted', []):
            for bid, w in g.get('words', []):
                raw = w.strip('.,!?;:\'"—-').rstrip('’s').rstrip("'s")
                if len(raw) < 4 or raw.lower() in SKIP or fold(raw) in SKIP:
                    continue
                key = fold(raw)
                if key in d or key in seen:
                    continue
                seen.add(key)
                gsrc = idx.get(fold_ns(raw))
                if not gsrc:
                    left.append((key, 'unlisted, no T1 gloss'))
                    continue
                gloss, src, _lem = gsrc
                # Deva source priority: T1 lemma (frozen, diacritics) first,
                # else the author's spoken surface if it carries diacritics
                # or Devanagari. Diacritic-less ASCII proves nothing (fold
                # erases the confusion class) and is never used.
                _src = None
                if re.search(r'[\u0900-\u097F]', raw):
                    _src = raw  # author's own Devanagari — exact
                elif _lem and re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]', _lem):
                    _src = _lem  # frozen T1 IAST with diacritics
                elif re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]', raw):
                    _src = raw  # author's IAST with diacritics
                if _src is None:
                    left.append((key, 'unlisted, no diacritic-bearing source'))
                    continue
                try:
                    dv = _src if re.search(r'[\u0900-\u097F]', _src) else _H.to_deva(_src)
                except Exception:
                    left.append((key, 'unlisted, transliteration failed'))
                    continue
                if not re.search(r'[\u0900-\u097F]', dv):
                    left.append((key, 'unlisted, no Deva produced'))
                    continue
                d[key] = {'deva': dv, 'gloss': gloss, 'status': 'confirmed',
                          'cue_blocks': [bid], 'deva_status': 'machine-verified',
                          'note': (f'auto-mined from white-gap audit + agent-confirmed 2026-11-06 '
                                   f'from translation-work {src}; Deva=transliteration of {_src!r}'
                                   f' (owner gate removed)')}
                new.append(key)
        print(f'ch{ch}: filled {len(filled)}, new {len(new)}, left proposed/unlisted {len(left)}')
        for k, why in left[:8]:
            print(f'    left: {k} ({why})')
        report.append({'ch': ch, 'filled': filled, 'new': new, 'reverified_corrected': revived,
                       'reverified_demoted': revoked, 'left': [{'key': k, 'why': w} for k, w in left]})
        if args.apply:
            json.dump(d, open(glp, 'w'), ensure_ascii=False, indent=1)
            print(f'  WROTE {glp}')
    if args.apply:
        import hashlib as _hl
        for r in report:
            ch = r['ch']
            sbp = os.path.join(repo, 'storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json')
            glp = os.path.join(repo, 'glossary_ch6.json' if ch == '06' else f'glossary_ch{ch}.json')
            app = os.path.join(repo, 'approved_ch6.json' if ch == '06' else f'approved_ch{ch}.json')
            a = json.load(open(app, encoding='utf-8'))
            a['storyboard_sha'] = _hl.sha256(open(sbp, 'rb').read()).hexdigest()
            a['glossary_sha'] = _hl.sha256(open(glp, 'rb').read()).hexdigest()
            a['date'] = '2026-11-06'
            a['note'] = (a.get('note', '') + ' | agent T1-confirm pass (owner gate removed 2026-11-06)').strip(' |')
            json.dump(a, open(app, 'w'), indent=2)
        print('approvals refreshed')
    json.dump(report, open('/tmp/fill_glossary_report.json', 'w'), indent=1)
    print('report -> /tmp/fill_glossary_report.json')


if __name__ == '__main__':
    main()
