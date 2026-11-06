#!/usr/bin/env python3
"""Shiva verse-gloss backlog helpers (proposed-only, never confirmed).

Two deterministic, judgment-free operations on shiva verse_gloss files
(render-neutral: video shows confirmed entries only; approvals pin
storyboard+glossary, never verse_gloss):

1. backfill-bids: every entry carries the bids it matches (match_key via
   the shared holds.verse_match_key, same function the renderer uses).
   Fixes stale bookkeeping where an entry exists and matches but names
   no bids (e.g. s27) — verse-gloss-missing keys off bids.

2. mine-positional: for a multi-line Deva chant with NO entry, if the
   strict canon shape holds (verse Deva block, immediately followed by a
   granny IAST repeat with EQUAL match_key, followed by a granny
   non-IAST English gloss, no other verse within +-2 blocks), file a
   PROPOSED entry {match_key, bids, literal=gloss text, final=''}.
   Cross-unit echoes, recaps with ref prefixes, multi-verse runs, and
   anything ambiguous are skipped — scholar territory, listed not filed.

Confirming is an owner/scholar act (bulk-confirm), never done here.
Usage: python3 mine_shiva_verse_gloss.py [--apply]  (dry-run by default)
"""
import copy
import json
import glob
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))

import holds as H


def key_of(text):
    try:
        return H.verse_match_key(text)
    except Exception:
        return None


def is_verse(b):
    return b.get('type') == 'verse' and b.get('voice') == 'verse'


def is_granny(b):
    return b.get('voice') == 'granny' and b.get('type') in ('narration', 'dialogue')


IAST_RE = re.compile(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]')


def is_iast_repeat(text):
    toks = [w.strip('.,!?;:\'"—-()') for w in text.split()]
    toks = [t for t in toks if t]
    if not toks or len(toks) > 12 or re.search(r'[\u0900-\u097F]', text):
        return False
    dia = sum(1 for t in toks if IAST_RE.search(t))
    return dia >= 2 and dia / len(toks) >= 0.5


def load_vg(vgp):
    try:
        with open(vgp, encoding='utf-8') as f:
            doc = json.load(f)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError) as e:
        print(f'WARNING skipping unreadable {os.path.basename(vgp)}: {e}')
        return None


def audit_unit(sb_path):
    """Returns (backfill {key: [bids]}, mine [{entry}], skip_reasons)."""
    sb = json.load(open(sb_path, encoding='utf-8'))
    blocks = sb['blocks']
    lane = H.lane_for(os.path.abspath(sb_path)).get('lane', '')
    assert lane == 'shiva', f'refusing non-shiva unit: {sb_path}'
    vgp = H.lane_for(os.path.abspath(sb_path))['verse']
    vg = load_vg(vgp) if vgp and os.path.exists(vgp) else {}
    have_keys = {v.get('match_key', k) for k, v in vg.items() if isinstance(v, dict)}
    key_to_bids = {}
    for b in blocks:
        if not is_verse(b) or b['id'] == 'b_opener':
            continue
        k = key_of(b['text'])
        if k:
            key_to_bids.setdefault(k, []).append(b['id'])
    backfill, mine, skipped = {}, [], []
    for k, bids in key_to_bids.items():
        if k in have_keys:
            continue
        # multi-line Deva chant without an entry: strict canon pattern?
        cands = [b for b in blocks if b['id'] in bids and len(b['text'].split()) > 3
                 and re.search(r'[\u0900-\u097F]', b['text'])]
        for b in cands:
            i = next(i for i, x in enumerate(blocks) if x['id'] == b['id'])
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            nxt2 = blocks[i + 2] if i + 2 < len(blocks) else None
            near_verses = [x['id'] for x in blocks[max(0, i - 2):i + 3]
                           if is_verse(x) and x['id'] != b['id']]
            if (nxt and is_granny(nxt) and is_iast_repeat(nxt['text'])
                    and key_of(nxt['text']) == k and nxt2 and is_granny(nxt2)
                    and not is_iast_repeat(nxt2['text']) and not near_verses):
                mine.append({'key': k, 'bids': [b['id']],
                             'literal': nxt2['text'].strip()[:500], 'final': '',
                             'why': f"{b['id']} chant -> {nxt['id']} IAST repeat (key-equal) -> {nxt2['id']} gloss"})
            else:
                skipped.append((b['id'], 'no strict chant->repeat->gloss run'))
    for k, v in vg.items():
        if isinstance(v, dict) and not v.get('bids'):
            mk = v.get('match_key', k)
            if mk in key_to_bids:
                backfill[k] = key_to_bids[mk]
    return backfill, mine, skipped


def main():
    apply = '--apply' in sys.argv
    units = [a for a in sys.argv[1:] if re.fullmatch(r's\d{2}', a)]
    lane_paths = sorted(glob.glob('/home/ubuntu/tantrasara/shiva/verse_gloss_s*.json'))
    if units:
        lane_paths = [p for p in lane_paths
                      if os.path.basename(p) == f'verse_gloss_{units[0]}.json' or
                      any(os.path.basename(p) == f'verse_gloss_{u}.json' for u in units)]
    tot_bf, tot_mine, tot_skip = 0, 0, []
    for vgp in lane_paths:
        m = re.search(r's(\d+)\.json$', os.path.basename(vgp))
        sb_path = f'/home/ubuntu/tantrasara/shiva/storyboards/storyboard_s{m.group(1)}.json'
        backfill, mine, skipped = audit_unit(sb_path)
        tot_skip.extend([(os.path.basename(vgp), b, w) for b, w in skipped])
        if not apply:
            tot_bf += len(backfill)
            tot_mine += len(mine)
            continue
        vg = load_vg(vgp)
        if vg is None:
            print(f'skipping {os.path.basename(vgp)} (unreadable; fix by hand, never auto-rebuild)')
            continue
        for k, bids in backfill.items():
            if isinstance(vg.get(k), dict):
                vg[k]['bids'] = sorted(set(vg[k].get('bids', []) + bids))
                tot_bf += 1
        for e in mine:
            ref = f"pos_{e['bids'][0]}"
            if ref not in vg:
                vg[ref] = {'bids': e['bids'], 'match_key': e['key'], 'match_score': None,
                           'literal': e['literal'], 'final': e['final'], 'status': 'proposed',
                           'note': f"positional mine (shiva canon chant->repeat->gloss); scholar bulk-confirm. {e['why']}"}
                tot_mine += 1
        import tempfile
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=os.path.dirname(vgp),
                                         delete=False) as f:
            json.dump(vg, f, ensure_ascii=False, indent=1)
            tmp = f.name
        os.replace(tmp, vgp)
    print(f'verse-gloss backlog: backfilled bids on {tot_bf} entries, mined {tot_mine} proposed entries'
          + ('' if apply else ' (dry-run)'))
    for s in tot_skip[:20]:
        print('  skip:', s)
    if tot_skip[20:]:
        print(f'  ... and {len(tot_skip) - 20} more skipped (scholar territory)')


if __name__ == '__main__':
    main()
