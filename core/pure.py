"""Pure core: deterministic rhythm + chunk policy. No I/O, no models.

Every function here is unit-tested (tests/test_pure.py) with fixtures from
real chapters, including the 2026-11-05 MMS killer groups. Builders import
from here; the inline copies are gone (single source, M30 pattern).
"""
import re

CRISP_BED = 2.8
CHUNK_WORDS = 200  # groups above this align in silence-split halves (proven)


def bed_after(group, following, crisp=CRISP_BED):
    """Deterministic bed after a group (clip rhythm table, canonical)."""
    text = ' '.join(b.get('directed', b['text']) for b in group)
    if group[0]['type'] == 'title' or (following and following[0]['section'] != group[0]['section']):
        return 0.8
    if any(b['type'] == 'dialogue' for b in group):
        return 0.8
    if group[0]['voice'] == 'verse':
        if any(b['type'] == 'verse' and len(b['text'].split()) > 3 for b in group):
            return crisp
        return 0.6
    if '[long pause]' in text:
        return 0.8
    return 0.3


def should_chunk(n_words):
    return n_words > CHUNK_WORDS


def split_index(block_counts, cut_frac, n_disp):
    """Word index for the chunk cut, snapped to a block boundary so no
    block's words ever split across chunks. Pure port of the proven
    build_clip splitter."""
    at = int(n_disp * cut_frac)
    run, best, bestd = 0, 0, None
    for n in block_counts:
        run += n
        dd = abs(run - at)
        if bestd is None or dd < bestd:
            bestd, best = dd, run
    return min(max(best, 1), n_disp - 1)


def plan_groups(blocks):
    """The shared grouping rule: consecutive same-section same-voice;
    voice-none and figure/label/meta skipped (visual-only); opener kept
    as an opener-kind group. Reference implementation — builders resolve
    the same rule; tests assert parity on fixture storyboards."""
    groups, cur = [], []

    def flush():
        if cur:
            groups.append(cur[:])
            cur.clear()

    for b in blocks:
        if b['id'] == 'b_opener':
            flush()
            groups.append([dict(b, group_kind='opener')])
            continue
        if b['voice'] == 'none' or b.get('type') in ('figure', 'label', 'meta'):
            continue
        if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
            flush()
        cur.append(b)
    flush()
    return groups


def count_disp(group):
    return sum(len([w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)])
               for b in group if 'group_kind' not in b)
