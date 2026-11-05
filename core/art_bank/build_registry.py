#!/usr/bin/env python3
"""Build the trika art-bank registry (deterministic; re-run after P1 changes).

Sources of truth (pointers, never copies — except the spider exemplar,
which is the mechanism-standard and is vendored with provenance):
  translation-work/P1-INDEX.md  — seal/base/seed/rating/status per package
  translation-work/*/P1 seal files — the seal briefs themselves
  core/art_bank/seals/spider-song04-seal.md — vendored exemplar

Bank rule (from THE-WHOLE-CRAFT + P1-SONG04-SEAL §4-5): every entry needs
verse anchors + essence anchors, or PROPOSED status (queued, unproven).
No asset without a recipe. New seal = new base (spent-log), never reuse.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TW = Path('/root/translation-work')


def parse_p1_index():
    entries = []
    for line in (TW / 'P1-INDEX.md').read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 8 or cells[0] in ('#', '—') or cells[0].startswith('-'):
            continue
        if not re.fullmatch(r'(T2-\d+|\d+[a-g]?)', cells[0]):
            continue
        entries.append({
            'p1_id': cells[0], 'work': cells[1],
            'seal_file': cells[2].strip('`'),
            'seal': cells[3], 'base': cells[4], 'seed': cells[5],
            'rating': cells[6], 'p1_status': cells[7][:60],
        })
    return entries


QUEUE = [
    {'subject': 'mala', 'why': 'ch20 garland ceremony (malini/ratnamala); the counted circle that holds mantras',
     'keywords': ['mala', 'garland', 'malini', 'ratnamala', 'rosary', 'circle of names']},
    {'subject': 'mirror', 'why': 'recognition doctrine needs its glass; P1 #4/#2 mirrors exist as kin',
     'keywords': ['mirror', 'reflection', 'pratibimba', 'glass']},
    {'subject': 'knot', 'why': 'bondage-made-by-self; spider exemplar covers song04, generalize the knot',
     'keywords': ['knot', 'net', 'web', 'tangle', 'bondage', 'pasa']},
    {'subject': 'sun', 'why': 'bhāsvara crown; every seal climbs toward it — bank one reusable sun grammar',
     'keywords': ['sun', 'solar', 'gold', 'light', 'bhasvara', 'splendour']},
    {'subject': 'jar', 'why': 'one-dust-non-transfer (v37); the vessel that keeps dust from travelling',
     'keywords': ['jar', 'pot', 'vessel', 'kumbha', 'dust']},
    {'subject': 'door', 'why': 'un-shut door (P1 #3); threshold grammar for initiations (diksa-heavy ch20)',
     'keywords': ['door', 'threshold', 'gate', 'entrance', 'dikṣa', 'diksa']},
    {'subject': 'sea', 'why': 'still sea that spilled the sky (P1 #15); the untouched that holds everything',
     'keywords': ['sea', 'ocean', 'water', 'lake', 'river']},
    {'subject': 'mountain', 'why': 'ascent grammar; Kailāsa/Meru verticality for ladder chapters',
     'keywords': ['mountain', 'peak', 'kailasa', 'meru', 'hill', 'ascent']},
]


def main():
    p1 = parse_p1_index()
    entries = [{
        'id': 'spider-song04',
        'subject': 'spider',
        'kind': 'exemplar',
        'seal_brief': 'seals/spider-song04-seal.md',
        'provenance': 'vendored 2026-11-05 from translation-work/paramarthasara/P1-SONG04-SEAL.md (owner verdict: THIS IS THE ONE)',
        'seal': 'the knot that contains its own light, unwrapping into the sun',
        'base': 'bordered Solis page user1 (spent for song04)',
        'seed': '123 (keeper v4)',
        'status': 'OWNER-APPROVED-ANGLE',
        'verse_anchors': 'paramarthasara vv29-37', 'essence_anchors': 'C1 [0][1][2][3]',
        'keywords': ['spider', 'web', 'knot', 'thread', 'spin', 'tangle'],
    }]
    for e in p1:
        entries.append({
            'id': f"p1-{e['p1_id'].lower()}",
            'subject': e['seal'][:80],
            'kind': 'p1-pointer',
            'seal_brief': f"translation-work/{e['seal_file']}",
            'provenance': 'pointer — canonical file lives in translation-work (do not copy)',
            'seal': e['seal'], 'base': e['base'], 'seed': e['seed'],
            'rating': e['rating'], 'status': 'MACHINE_DRAFT',
            'p1_status': e['p1_status'], 'work': e['work'],
            'verse_anchors': 'see seal brief (required before render)',
            'essence_anchors': 'see seal brief (required before render)',
            'keywords': [],
        })
    for q in QUEUE:
        entries.append({'id': f"queue-{q['subject']}", 'kind': 'queued-subject',
                        'status': 'PROPOSED', **q,
                        'verse_anchors': 'unassigned', 'essence_anchors': 'unassigned'})
    reg = {'format': 'trika-art-bank/1',
           'law': 'every render needs verse+essence anchors (or PROPOSED stays queued); no asset without recipe; new seal = new base',
           'entries': entries}
    out = HERE / 'REGISTRY.json'
    out.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + '\n')
    kinds = {}
    for e in entries:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print(f'{out}: {len(entries)} entries {kinds}')


if __name__ == '__main__':
    sys.exit(main())
