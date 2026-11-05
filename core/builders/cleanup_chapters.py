#!/usr/bin/env python3
"""One-pass chapter cleanup: blurbs, duplicate titles, Keep reading,
citation tails. Run once; verified by audit + storyboard gates after.
Usage: python3 cleanup_chapters.py [ch14 ch15 ...] (default: all).
Scope to new chapters whenever positional overrides exist downstream —
text edits shift block IDs (learned 2026-11-03).
Also strips, learned from the TTS read-aloud pass 2026-11-03:
  Gmail attachment artifacts (U+2060 + 'Attachment.png'),
  standalone URL/domain lines, folio tails (' १२', ' १२ +2').
Voicing rules (build_storyboard.py, no text change, safe on frozen chapters):
  Devanagari DIGITS never voice a block (letters only);
  citation-only lines (URL + <10 other words) and ALL-CAPS witness labels
  route to meta, never spoken.
"""
import re, glob, sys

BLURB = re.compile(r'slang \w+ (retelling|adaptation)|slang (retelling|adaptation)|irreverent retelling', re.I)
CITE = re.compile(r'\s*(?:[A-Z][\w&.-]*(?: [A-Z][\w&.-]*){0,3}|[\w.-]+\.[\w.]+) \+\d\s*$')
PROV = ('Textual basis', 'Source note', 'Sources:', 'Textual sources')
DEVA_L = re.compile('[\\u0905-\\u0939\\u093E-\\u094D\\u0958-\\u0963]')
FOLIO = re.compile(r'\s*[०-९]+\s*(\+\d+)?\s*$')
ATTACH = re.compile('⁠?Attachment\\.png')
URL_LINE = re.compile(r'^(?:https?://\S+|[\w.-]+\.[a-z]{2,}(?:\.\w+)?)\s*$')

only = set(sys.argv[1:]) if len(sys.argv) > 1 else None
files = sorted(glob.glob('/home/ubuntu/tantrasara/chapters/ch*.md'))
if only:
    norm = {re.sub(r'^ch0*', '', o.lower()) or '0' for o in only}
    files = [f for f in files
             if (re.search(r'ch(\d+)', f).group(1).lstrip('0') or '0') in norm]

for f in files:
    lines = open(f, encoding='utf-8').read().splitlines()
    # drop duplicate title (first non-blank line == H1 text)
    if lines and lines[0].startswith('# '):
        for i in range(1, min(4, len(lines))):
            if lines[i].strip() == lines[0][2:].strip():
                print(f'{f.split("/")[-1]}: drop duplicate title')
                del lines[i]
                break
    out = []
    for l in lines:
        s = l.strip()
        if not s:
            out.append('')  # paragraph breaks are block boundaries — never drop
            continue
        s = re.sub(r'  +', ' ', ATTACH.sub('', s))  # gmail artifact, never spoken
        if URL_LINE.match(s):
            print(f'{f.split("/")[-1]}: drop URL line [{s[:60]}]')
            continue
        if not DEVA_L.search(s):
            ns = FOLIO.sub('', s)  # folio tails on prose ('witnesses. १२')
            if ns != s:
                print(f'{f.split("/")[-1]}: strip folio [{s[-24:]}]')
                s = ns.strip()
                if not s:
                    continue
        if s in ('/', '//'):
            continue  # lone danda markers
        # GRETIL archival / // line-end markers: notation, never voiced or shown
        s = re.sub(r'\s*//\s*$', '', s)
        s = re.sub(r'\s*/\s*$', '', s)
        if s.strip() == 'Keep reading':
            print(f'{f.split("/")[-1]}: drop Keep reading')
            continue
        if BLURB.search(s) and len(s.split()) > 8 and not s.startswith('#'):
            print(f'{f.split("/")[-1]}: drop blurb [{s[:60]}]')
            continue
        ns = CITE.sub('', s)
        if ns != s:
            print(f'{f.split("/")[-1]}: strip citation [{s[-40:]}]')
            s = ns
        out.append(s)
    open(f, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('done')
