#!/usr/bin/env python3
"""Draft per-chapter glossaries: IAST terms with appositive-mined glosses.
Usage: python3 mine_glossary.py
Every entry starts proposed (white until confirmed). Appositives
("TERM, the GLOSS" / "TERM is GLOSS") fill some; the rest get "".
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import json, os, re, glob, unicodedata

BASE = _vf.repo_root()
SKIP = {'shiva', 'shakti', 'tantrasara', 'tantraloka', 'kashmir', 'abhinavagupta',
        'siva', 'sakti', 't 肉'.strip(), 'guru', 'sutra', 'sutras', 'tantra'}

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

CAPS = 'ĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ'
WORD = f'[A-Za-zāīūṛṝḷṃḥṅñṭḍṇśṣ{CAPS}·-]+'

def main():
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument('--out', default=None, help='output dir for mined drafts (default: factory proposed/)')
    _p.add_argument('--chapters', default='02,03,04,05,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22')
    _a, _unknown = _p.parse_known_args()
    # Never overwrite series glossaries by default (postmortem: full-lane
    # remine wiped Deva citations). Factory writes to proposed/; promotion
    # to the series repo is an explicit owner action with --out=<series dir>.
    _factory_proposed = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'projects', 'tantrasara', 'proposed')
    outdir = _a.out or _factory_proposed
    os.makedirs(outdir, exist_ok=True)
    if os.path.abspath(outdir) == os.path.abspath(BASE):
        raise SystemExit('refusing to overwrite series glossaries: pass --out=<factory proposed dir>')
    for ch in [c.strip() for c in _a.chapters.split(',') if c.strip()]:
        sb = json.load(open(f'{BASE}/storyboard_ch{ch}.json'))
        terms = {}
        for b in sb['blocks']:
            if b['type'] not in ('narration', 'dialogue') or not b['text'].strip():
                continue
            for w in re.findall(WORD, b['text']):
                c = fold(w.strip('.,!?;:\'"—-'))
                if c in terms or len(c) < 4 or c in SKIP:
                    continue
                if not re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]', w):
                    continue
                terms[c] = b['id']
        gl = {}
        for k, bid in sorted(terms.items()):
            gl[k] = {'deva': '', 'gloss': '', 'status': 'proposed', 'cue_blocks': [bid],
                     'note': 'auto-mined; needs Deva + gloss review'}
        # appositive mining: "Term, the gloss" / "Term is gloss" / "Term — gloss"
        full = ' '.join(b['text'] for b in sb['blocks'] if b['type'] in ('narration', 'dialogue'))
        for k in list(gl):
            surf = None
            for w in re.findall(WORD, full):
                if fold(w.strip('.,!?')) == k:
                    surf = w.strip('.,!?')
                    break
            if not surf:
                continue
            m = re.search(re.escape(surf) + r'\s*,?\s+(?:the|a|an)\s+([^,.;]{3,60})', full)
            if m:
                gl[k]['gloss'] = m.group(0)[len(surf):].strip(' ,')[:80]
                gl[k]['note'] = 'appositive-mined, confirm'
        json.dump(gl, open(os.path.join(outdir, f'glossary_ch{ch}.proposed.json'), 'w'), ensure_ascii=False, indent=1)
        filled = sum(1 for v in gl.values() if v['gloss'])
        print(f'ch{ch}: {len(gl)} terms, {filled} appositive glosses -> {outdir}/glossary_ch{ch}.proposed.json')


if __name__ == '__main__':
    main()