#!/usr/bin/env python3
"""Verse-card defect detector: Deva without English + stale split-verse holds.

Finds, for one storyboard, the two verse-card bugs the owner caught on
unrendered units (tantrasara 16-22):

  verse-deva-no-english — a verse block whose video card carries Devanagari
    with no English literal/final underneath. The renderer (holds.render_hold,
    confirmed_only=True, i.e. exactly what build_clip passes) shows verse
    gloss English only from a CONFIRMED verse_gloss entry (literal or final
    present) keyed by verse_match_key(block text), or full term layers for a
    single-word chant that hits a confirmed glossary term. Everything else —
    missing entry, proposed-only entry, stale bids, a TRANSLITERATION label
    polluting the key, or a split-off roman half whose key can never match
    the full-verse key — renders Devanagari-only. This check replays that
    exact decision (same shared helpers, same confirmed-only gating), so a
    flag means the shipped card really has no English.

  stale-verse-hold — one Sanskrit verse scattered over several blocks
    (Deva block + roman-only verse half + IAST tail voiced granny/man),
    so the card sequence shows machine-regenerated Devanagari instead of
    the author's citation, and the following narration holds a stale
    half-card instead of the verse. Structural signatures (no timing
    estimates):
    - a verse block carrying a bare TRANSLITERATION / ORIGINAL SANSKRIT
      label line (the split marker; the halves live in neighbouring blocks),
    - adjacent verse blocks with EQUAL verse_match_key but different bids
      (same verse, two cards — key equality is proof, not heuristic),
    - a roman-only verse block that is not a confirmed glossary term
      (its card Deva is machine-regenerated via to_deva, never the
      author's citation),
    - a granny/man block adjacent to a verse block that is mostly IAST
      (the misvoiced tail: the caster's every-token-Sanskrit rule sank on
      one ASCII word such as 'kim', so the tail fell through to granny).

Single-word chants that hit no glossary term are NOT flagged here: the
white-hold antidote (audit_white_gaps.py UNLISTED) already classes them
as mining backlog, not a bug. b2 (chapter-name chant, every chapter) is
excluded like verse-gloss-missing excludes it.

Usage: python3 check_verse_cards.py <storyboard.json>
  prints the two finding lists (all bids, untruncated). check_issues.py
  imports find_no_english / find_split_spans and files them as issues.
"""
import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, '..', 'contract'))

import holds as _H

try:
    from build_storyboard import IAST as _IAST_RE
except Exception:
    _IAST_RE = re.compile(r'[āīūṛṝḷḹṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]')

DEVA_RE = re.compile(r'[\u0900-\u097F]')
SPLIT_LABELS = ('TRANSLITERATION', 'ORIGINAL SANSKRIT')
SPLIT_LABEL_RE = re.compile(r'^(IAST\s+)?TRANSLITERATION$|^ORIGINAL\s+SANSKRIT$')
TAIL_DIACRITIC_MIN = 2
TAIL_DIACRITIC_FRAC = 0.5
TAIL_MAX_WORDS = 12


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def confirmed_views(sb_path):
    """Mirror build_clip's _gl / _vg construction EXACTLY.

    _gl: confirmed glossary terms with gloss, literal only when its own
    literal_status is confirmed (require_list_geometry gate mirrors the
    same rule — an unconfirmed literal must never widen a card or a check).
    _vg: verse_gloss entries keyed by match_key (entry's match_key field,
    falling back to the dict key), exactly like build_clip lines 447-448.
    Missing files behave like build_clip: empty views, never a crash.
    """
    lane = _H.lane_for(os.path.abspath(sb_path))
    gl_raw = json.load(open(lane['glossary'], encoding='utf-8')) \
        if os.path.exists(lane['glossary']) else {}
    gl = {}
    for k, v in (gl_raw or {}).items():
        if not (isinstance(v, dict) and v.get('status') == 'confirmed' and v.get('gloss')):
            continue
        gl[k] = {'deva': v.get('deva', ''), 'gloss': v.get('gloss', ''),
                 'literal': v.get('literal', '') if v.get('literal_status') == 'confirmed' else ''}
    vg_raw = {}
    vgp = lane.get('verse')
    if vgp and os.path.exists(vgp):
        vg_raw = json.load(open(vgp, encoding='utf-8')) or {}
    vg = {}
    for k, v in vg_raw.items():
        if isinstance(v, dict):
            vg[v.get('match_key', k)] = v
    return gl, vg


def card_english(block, gl, vg):
    """Would the video card for this verse block carry English?

    Renderer-identical to holds.render_hold (confirmed_only=True):
    a single-word chant resolving to a confirmed glossary term renders the
    full term layers (gloss/literal lines); any other verse line renders
    verse-gloss English only from a confirmed entry with literal or final.
    Returns (has_english, reason).
    """
    text = block.get('text', '')
    toks = text.split()
    single = len(toks) <= 3
    if single:
        key = _fold(text.strip('.,!?;:\'"—-'))
        if key not in gl and DEVA_RE.search(text):
            try:
                key = _fold(_H.to_iast(text.strip('.,!?;:\'"—-')))
            except Exception:
                pass
        hit = gl.get(key)
        if isinstance(hit, dict) and (hit.get('gloss') or hit.get('literal')):
            return True, f'single chant resolves to confirmed term {key}'
        return False, f'single chant with no confirmed term ({key})'
    key = _H.verse_match_key(text)
    hit = vg.get(key)
    if isinstance(hit, dict) and hit.get('status') == 'confirmed' \
            and (hit.get('literal') or hit.get('final')):
        return True, 'confirmed verse_gloss with literal/final'
    if not isinstance(hit, dict):
        return False, 'no verse_gloss entry for match_key'
    if hit.get('status') != 'confirmed':
        return False, f"verse_gloss {hit.get('status')} (video shows confirmed only)"
    return False, 'confirmed verse_gloss with empty literal+final'


def _is_split_label_block(block):
    lines = [ln.strip() for ln in block.get('text', '').splitlines() if ln.strip()]
    return any(ln in SPLIT_LABELS or SPLIT_LABEL_RE.match(ln) for ln in lines)


def _tail_score(text):
    toks = [w.strip('.,!?;:\'"—-()') for w in text.split()]
    toks = [t for t in toks if t]
    if not toks or len(toks) > TAIL_MAX_WORDS or DEVA_RE.search(text):
        return 0.0, 0
    dia = sum(1 for t in toks if _IAST_RE.search(t))
    return dia / len(toks), dia


def find_split_spans(blocks, lane='tantrasara'):
    """Structural split-verse spans. Returns [{bids, patterns, detail}].

    lane matters for exactly one pattern: iast-tail-misvoiced. In
    tantrasara the caster's every-token-Sanskrit rule owns voice casting,
    so a granny IAST tail adjacent to a verse is a fall-through defect.
    In shiva, chant -> IAST-repeat (granny) -> gloss is the owner-blessed
    unit canon (Nov-4 restructure), so tails are not flagged there.
    Label / pair / roman-half patterns are lane-agnostic (a Deva-less
    verse card regenerates Devanagari in every lane)."""
    by_id = {b['id']: b for b in blocks}
    order = [b['id'] for b in blocks]
    pos = {bid: i for i, bid in enumerate(order)}
    roles = {}  # bid -> set(patterns)

    def tag(bid, pattern):
        roles.setdefault(bid, set()).add(pattern)

    for i, b in enumerate(blocks):
        # b2 is the chapter-name chant (title line, never a T1 root verse)
        # in tantrasara only — shiva b2s are real sutra chants.
        if b.get('type') != 'verse' or (b['id'] == 'b2' and lane == 'tantrasara'):
            continue
        if _is_split_label_block(b):
            tag(b['id'], 'split-label')
        if DEVA_RE.search(b.get('text', '')):
            continue
        # roman-only verse block. A >3-token IAST chant is never a glossary
        # term (terms are short) — its card Deva is machine-regenerated and
        # its key can never match a full-verse verse_gloss entry.
        # Short (<=3-token) roman singles are term candidates (UNLISTED
        # mining backlog per the white-hold antidote, not a split) unless
        # proven otherwise: same-key-pair below, or sitting inside a
        # labelled split (adjacent to a split-label block, e.g. b823).
        toks = b.get('text', '').split()
        if len(toks) > 3:
            tag(b['id'], 'roman-only-verse')
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(blocks) and _is_split_label_block(blocks[j]):
                tag(b['id'], 'roman-only-verse')
                break
    # equal-key adjacent verse pairs: same verse, two cards (proof, not guess)
    for i in range(len(blocks) - 1):
        a, c = blocks[i], blocks[i + 1]
        if a.get('type') != 'verse' or c.get('type') != 'verse':
            continue
        if lane == 'tantrasara' and (a['id'] == 'b2' or c['id'] == 'b2'):
            continue
        try:
            if _H.verse_match_key(a['text']) == _H.verse_match_key(c['text']):
                tag(a['id'], 'same-key-pair')
                tag(c['id'], 'same-key-pair')
        except Exception:
            pass
    # misvoiced IAST tails: granny/man block, mostly IAST, adjacent to verse.
    # Second pass chains continuations: a tail-half followed by another
    # IAST tail (b1931 then b1932) belongs to the same split run even
    # though only the first touches a verse block.
    # TANTRASARA ONLY (owner canon differs per lane): shiva voices the
    # IAST repeat with granny by Nov-4 owner call, so tails there are
    # chant -> IAST -> gloss canon, never a fall-through defect.
    if lane == 'tantrasara':
        for _pass in range(2):
            for i, b in enumerate(blocks):
                if b.get('voice') not in ('granny', 'man'):
                    continue
                if b.get('type') not in ('narration', 'dialogue'):
                    continue
                if b['id'] in roles:
                    continue
                frac, dia = _tail_score(b.get('text', ''))
                if dia < TAIL_DIACRITIC_MIN or frac < TAIL_DIACRITIC_FRAC:
                    continue
                neighbours = []
                if i > 0:
                    neighbours.append(blocks[i - 1])
                if i + 1 < len(blocks):
                    neighbours.append(blocks[i + 1])
                if any(n.get('type') == 'verse' or n['id'] in roles for n in neighbours):
                    tag(b['id'], 'iast-tail-misvoiced')
    if not roles:
        return []
    # merge contiguous flagged bids into spans (label+halves+tails are
    # contiguous by construction; lone roman halves stand alone)
    flagged = sorted(roles, key=lambda bid: pos.get(bid, 10 ** 9))
    spans, cur = [], []
    for bid in flagged:
        if cur and pos.get(bid, 10 ** 9) == pos.get(cur[-1], 10 ** 9) + 1:
            cur.append(bid)
        else:
            if cur:
                spans.append(cur)
            cur = [bid]
    if cur:
        spans.append(cur)
    # Pure single+single same-key pairs (two one-word term chants, e.g. an
    # IAST term followed by its Deva) are term re-chants, not split verses:
    # the newest card holds correctly, nothing stale. They stay under
    # glossary/audit discipline (UNLISTED backlog or proposed-awaiting-
    # confirm), never stale-verse-hold. Keep a span only if it carries a
    # multi-line member or a label/tail pattern.
    out = []
    for span in spans:
        pats = sorted({p for bid in span for p in roles[bid]})
        if not (set(pats) & {'split-label', 'iast-tail-misvoiced'}) and not any(
                len(by_id.get(bid, {}).get('text', '').split()) > 3 for bid in span):
            continue
        parts = []
        for bid in span:
            b = by_id.get(bid, {})
            parts.append(f"{bid}[{b.get('type')}/{b.get('voice')}:{','.join(sorted(roles[bid]))}]")
        # neighbour context: the verse this split run continues/interrupts
        # (not flagged itself — a complete Deva+IAST verse in one block —
        # but the run only makes sense beside it).
        ctx = []
        lo, hi = pos.get(span[0], 0), pos.get(span[-1], 0)
        for k in (lo - 1, hi + 1):
            if 0 <= k < len(blocks) and blocks[k].get('type') == 'verse' \
                    and blocks[k]['id'] not in span:
                ctx.append(blocks[k]['id'])
        out.append({'bids': span, 'patterns': pats,
                    'detail': 'split verse span: ' + ' '.join(parts)
                    + (f" continues/interrupts verse {','.join(ctx)}" if ctx else "")})
    return out


def find_no_english(blocks, gl, vg, split_bids=(), lane='tantrasara'):
    """Verse blocks whose video card carries no English (b2 excluded in
    tantrasara only — shiva b2s are real sutra chants).

    Scope: multi-line blocks (>3 tokens) plus split-span members (roman
    halves are short but still render regenerated Deva with no English).
    Single-word chants outside splits stay under glossary/audit discipline
    (audit_white_gaps UNLISTED = mining backlog, not a bug).
    """
    split_set = set(split_bids)
    out = []
    for b in blocks:
        if b.get('type') != 'verse':
            continue
        if b['id'] == 'b2' and lane == 'tantrasara':
            continue
        multi = len(b.get('text', '').split()) > 3
        if not multi and b['id'] not in split_set:
            continue
        has, reason = card_english(b, gl, vg)
        if not has:
            out.append({'bid': b['id'], 'reason': reason})
    return out


def check(sb_path):
    """Full verse-card check for one storyboard. Returns dict with
    no_english [{bid, reason}] and spans [{bids, patterns, detail}],
    (glossary, verse_gloss) confirmed views included for callers.
    Shared by the CLI and check_issues.py so both always agree.
    """
    sb = json.load(open(sb_path, encoding='utf-8'))
    blocks = sb['blocks']
    gl, vg = confirmed_views(sb_path)
    lane = _H.lane_for(os.path.abspath(sb_path)).get('lane', 'tantrasara')
    gl_keys = set(gl)
    kept = []
    for sp in find_split_spans(blocks, lane):
        nbids = []
        for bid in sp['bids']:
            b = next(x for x in blocks if x['id'] == bid)
            if b.get('type') == 'verse' and not DEVA_RE.search(b.get('text', '')):
                if _fold(b.get('text', '').strip('.,!?;:\'"—-')) in gl_keys:
                    continue  # confirmed term card: authoritative Deva
            nbids.append(bid)
        if not nbids:
            continue
        order = [x['id'] for x in blocks]
        ctx = []
        lo, hi = order.index(nbids[0]), order.index(nbids[-1])
        for k in (lo - 1, hi + 1):
            if 0 <= k < len(blocks) and blocks[k].get('type') == 'verse' \
                    and blocks[k]['id'] not in nbids:
                ctx.append(blocks[k]['id'])
        kept.append({'bids': nbids, 'patterns': sp['patterns'],
                     'detail': 'split verse span: ' + ' '.join(
                         f"{bid}[{next(x for x in blocks if x['id']==bid).get('type')}/"
                         f"{next(x for x in blocks if x['id']==bid).get('voice')}]"
                         for bid in nbids) + f" patterns={','.join(sp['patterns'])}"
                     + (f" continues/interrupts verse {','.join(ctx)}" if ctx else "")})
    split_bids = {bid for sp in kept for bid in sp['bids']}
    return {'no_english': find_no_english(blocks, gl, vg, split_bids, lane),
            'spans': kept, 'gl': gl, 'vg': vg}


def main():
    sb_path = sys.argv[1]
    res = check(sb_path)
    sb = json.load(open(sb_path, encoding='utf-8'))
    print(f'verse-card check: {len(sb["blocks"])} blocks, '
          f'{len(res["gl"])} confirmed terms, {len(res["vg"])} verse_gloss entries')
    print(f'no-english verse cards ({len(res["no_english"])}):')
    for f in res['no_english']:
        print(f"  {f['bid']}: {f['reason']}")
    print(f'stale split-verse spans ({len(res["spans"])}):')
    for sp in res['spans']:
        print(f"  {sp['bids']}: {sp['detail'][:220]}")
    print('VERSE-CARDS ' + ('RED' if (res['no_english'] or res['spans']) else 'GREEN'))


if __name__ == '__main__':
    main()
