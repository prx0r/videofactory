#!/usr/bin/env python3
"""Shiva script-standardization checker: canon shape + TTS-ready text.

SHIVA ONLY — tantrasara storyboards are finished/frozen, and this checker
encodes the shiva series canon (CANONICAL-FLOW.md, Nov-4 owner verbatim +
Nov-4 restructure). Other lanes return an empty report.

Canon (machine-checkable part only — taste, funny presence, literal
quality, and pacing stay with owner/ears by design):
  S1 opener: b_opener bell block present (policy noted, never flagged —
    the bell rule is engine-owned: bells stay on s00/s01/s23/s33 only).
  S2 b1 is title/granny (the sutra ref; spoken-ref silence is engine-owned,
    noted not flagged).
  S3 book marker (BOOK I/II/III title block) exists iff unit in
    {s01, s23, s33} — position-agnostic (s33's sits at b109).
  S4 every non-s00 unit has >=1 verse chant; s00 has none.
  S5 "Literal:"/"Gloss:"/"Interpretive gloss:" labels never voiced
    (restructure stripped them; regression guard).
  S6 every multi-word DEVA chant is followed within 2 blocks by its IAST
    repeat (key-matched, any voice — re-chant vs repeat is
    intent-ambiguous, so voice is not judged). Self-contained bilingual
    blocks (Deva+IAST mixed, e.g. s29 alphabet lesson) and cross-unit
    echoes (IAST whose Deva aired in the chant's home unit, e.g. recap
    verses, s17 b32 = s02) are exempt by construction.

TTS-ready (mechanical delivery — Fish must never guess):
  T1 no leading junk: blocks starting with whitespace/punctuation/dash
    fragments (the two morphology suffixes -yoh/-at need an explicit
    voicing decision + probe_rough, never silent acceptance).
  T2 no lone-diacritic blocks (single combining char voiced = garbage).
  T3 no embedded label lines (TRANSLITERATION / ORIGINAL SANSKRIT /
    TEXTUAL|SOURCE NOTE as a line inside a non-label block — split to
    label/meta + rebuild).
  T4 no URLs, markdown, citation tails, read-more/keep-reading.
    "Next:" trailers are explicitly EXCLUDED (canon outro, owner-blessed).
  Enumeration runs (short fragments, no terminal) are list patter, never
  flagged — list-stack cards own them; colon-ender beats and dash
  handoffs are direction devices, not defects.

Preservation law: prescriptions never author prose. Reordering is free;
text edits are measured by word-multiset overlap and must keep >=95%
(author's words, minus stripped labels/junk only). Anything bigger is a
restructure, not a finetune — owner call.

Usage: python3 check_canon.py <storyboard.json>
check_issues.py imports check() and files canon-shape / tts-ready
issues (both needs-owner: reblock/rebuild or probe+reword).
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

BOOK_UNITS = {'01', '23', '33'}
BOOK_RE = re.compile(r'BOOK\s+[IVX]+\s+—')
LABEL_LINES = ('TRANSLITERATION', 'ORIGINAL SANSKRIT', 'IAST TRANSLITERATION')
NOTE_RES = (r'^TEXTUAL NOTE', r'^SOURCE NOTE')
LEAD_JUNK_RE = re.compile(r'^[\s.,;:!?\u00bb\u201d\u2014\u2013-]')
LONE_DIACRITIC_RE = re.compile(r'^[\u0900-\u097F]$')


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def _lane(sb_path):
    try:
        return H.lane_for(os.path.abspath(sb_path)).get('lane', '')
    except Exception:
        return ''


def _unit(sb_path):
    m = re.search(r's(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '').zfill(2)


def find_shapes(blocks, unit):
    """Canon-shape findings: [{bid, reason}]."""
    out = []
    by_id = {b['id']: b for b in blocks}
    # S1/S2: b1 title/granny (ref header source; silence is engine-owned)
    b1 = by_id.get('b1')
    if not b1 or b1.get('type') != 'title' or b1.get('voice') != 'granny':
        out.append({'bid': 'b1', 'reason': 'b1 must be the spoken title/ref line (title/granny)'})
    # S3: book marker iff book-opener unit
    markers = [b['id'] for b in blocks
               if b.get('type') == 'title' and BOOK_RE.search(b.get('text', ''))]
    if unit in BOOK_UNITS and not markers:
        out.append({'bid': 'b1', 'reason': f'book opener {unit} needs its BOOK marker title block'})
    if unit not in BOOK_UNITS and markers:
        out.append({'bid': markers[0], 'reason': f'BOOK marker only belongs on s01/s23/s33, found in {unit}'})
    # S4: chant coverage (s00: none by canon)
    verses = [b for b in blocks if b.get('type') == 'verse' and b.get('voice') == 'verse'
              and b['id'] != 'b_opener']
    if unit == '00':
        if verses:
            out.append({'bid': verses[0]['id'], 'reason': 's00 never chants (no sutra in it)'})
    elif not verses:
        out.append({'bid': 'b1', 'reason': f'{unit} has no verse chant'})
    # S5: voiced Literal:/Gloss: labels
    for b in blocks:
        if b.get('voice') in ('none',) or b['id'] == 'b_opener':
            continue
        if re.match(r'^(Literal|Gloss|Interpretive gloss)\s*:', b.get('text', '').strip(), re.I):
            out.append({'bid': b['id'], 'reason': 'voiced gloss label — canon says the literal is spoken without its label'})
    # S6: every multi-word Deva chant followed within 2 blocks by IAST repeat
    for i, b in enumerate(blocks):
        if b.get('type') != 'verse' or b.get('voice') != 'verse':
            continue
        deva, roman = H.split_scripts(b['text'])
        if not deva or len(b['text'].split()) <= 3:
            continue
        if roman:
            continue  # self-contained bilingual block (alphabet lesson etc.)
        try:
            want = H.verse_match_key(b['text'])
        except Exception:
            continue
        found = False
        for nb in blocks[i + 1:i + 3]:
            if nb.get('id') == 'b_opener' or nb.get('voice') == 'none':
                continue
            try:
                if H.verse_match_key(nb['text']) == want:
                    found = True
                    break
            except Exception:
                continue
        if not found:
            out.append({'bid': b['id'],
                        'reason': 'Deva chant with no IAST repeat in the next 2 blocks (canon: chant -> IAST -> gloss)'})
    return out


def find_tts_ready(blocks):
    """TTS-delivery findings: [{bid, reason}]. Mechanical only."""
    out = []
    for b in blocks:
        if b['id'] == 'b_opener' or b.get('voice') == 'none':
            continue
        t = b.get('text', '')
        if not t.strip():
            continue
        if LEAD_JUNK_RE.match(t):
            out.append({'bid': b['id'],
                        'reason': f'leading junk {t[:20]!r} — TTS will mangle it; reword (suffix fragments need a voicing decision + probe_rough) or strip'})
            continue
        if LONE_DIACRITIC_RE.match(t.strip()):
            out.append({'bid': b['id'], 'reason': 'lone diacritic block voiced — garbage audio; drop or voice deliberately'})
            continue
        for ln in t.splitlines():
            s = ln.strip()
            if s in LABEL_LINES:
                out.append({'bid': b['id'], 'reason': f'embedded label line {s!r} in a {b["type"]} block — split to label/meta + rebuild'})
                break
            if any(re.match(p, s) for p in NOTE_RES):
                out.append({'bid': b['id'], 'reason': f'source-note line voiced as narration — file as meta, never voiced'})
                break
        else:
            if re.search(r'https?://|www\.|\.(com|org|net)\b', t):
                out.append({'bid': b['id'], 'reason': 'URL in voiced text — strip (links never speak)'})
            elif re.search(r'\*\*|__.+__|^#{1,6}\s', t, re.M):
                out.append({'bid': b['id'], 'reason': 'markdown remnant in voiced text — strip'})
            elif re.search(r'<source|\(\+\d+\)\s*$', t):
                out.append({'bid': b['id'], 'reason': 'citation tail in voiced text — strip (M13 blanks preserved)'})
            elif re.search(r'(?i)read more|keep reading', t):
                # NOTE: Next:/Keep: trailers are canon outros, excluded.
                out.append({'bid': b['id'], 'reason': '"read more/keep reading" trailer — strip (outros stay spoken only via Next: lines)'})
    return out


def check(sb_path):
    """Full canon check. Non-shiva lanes return empty (tantrasara frozen)."""
    if _lane(sb_path) != 'shiva':
        return {'shapes': [], 'hygiene': [], 'skipped': 'non-shiva lane'}
    sb = json.load(open(sb_path, encoding='utf-8'))
    blocks = sb['blocks']
    unit = _unit(sb_path)
    return {'shapes': find_shapes(blocks, unit),
            'hygiene': find_tts_ready(blocks),
            'skipped': None}


def main():
    sb_path = sys.argv[1]
    res = check(sb_path)
    if res.get('skipped'):
        print(f'canon check: skipped ({res["skipped"]})')
        return
    print(f'canon-shape findings ({len(res["shapes"])}):')
    for f in res['shapes']:
        print(f"  {f['bid']}: {f['reason'][:160]}")
    print(f'tts-ready findings ({len(res["hygiene"])}):')
    for f in res['hygiene']:
        print(f"  {f['bid']}: {f['reason'][:160]}")
    print('CANON ' + ('RED' if (res['shapes'] or res['hygiene']) else 'GREEN'))


if __name__ == '__main__':
    main()
