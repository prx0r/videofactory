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


def recursive_split_index(block_counts, n_disp, target_frac=0.5):
    """Cut index for RECURSIVE chunking (build_clip MMS splitter).

    Prefers a real block boundary strictly inside the span (so blocks are
    never split across align pieces), nearest the target fraction of the
    words. When no interior boundary exists — one block alone exceeds the
    pressure ceiling — it falls back to a word-middle cut, which still
    keeps a strict interior index. That guarantee matters: a split that
    cannot shrink (returns 0 or n_disp) loops forever, so this function
    ALWAYS returns 1 <= at <= n_disp - 1 for n_disp >= 2.
    Pure and unit-tested (the "block-boundary snap lives in pure core"
    contract).
    """
    if n_disp < 2:
        return 0
    target = n_disp * target_frac
    run, best, bestd, lo = 0, None, None, 0
    for c in block_counts:
        run += c
        if lo < run < n_disp:
            dd = abs(run - target)
            if bestd is None or dd < bestd:
                bestd, best = dd, run
        lo = run
    if best is not None:
        return best
    return max(1, min(n_disp - 1, int(round(target))))


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


def motion_applies(base_kind):
    """The staging law (owner call 2026-11-05): motion (draw/clip spans and
    completion holds) renders ONLY on white. Chant, cue, persist, thumbnail
    and dialogue-entry cards always win — Sanskrit hold, deliberate blank,
    then draw. Never Sanskrit straight into draw."""
    return base_kind == 'white'
