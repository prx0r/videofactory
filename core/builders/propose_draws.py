#!/usr/bin/env python3
"""Propose sleepdraw seals for white-hold art gaps (machine-proposed, owner disposes).

Reads a holds timeline (review/chNN/timeline.md, WHITE entries) + the chapter
storyboard, drafts one hermetic seal prompt per gap via sleepdraw's
mcp_server.seal_prompt. Output stages in-factory at
projects/<lane>/proposed/draws_chNN.proposed.json — draws_for matches
draws_chNN.json exactly, so staged files NEVER render. Owner promotes: render
each asset (sleepdraw MCP render_seal with explicit confirm_paid), copy to the
series drops dir as draws_chNN.json {start_bid: {asset, complete_bid, clear,
fade, why}} — draws_for fails loud on missing fields.

Usage: python3 propose_draws.py <storyboard.json> <timeline.md> [out.json] [--white-map review/white-map.md]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lane_api import for_path  # noqa: E402

FACTORY_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

SLEEPDRAW_ROOT = os.environ.get('SLEEPDRAW_ROOT', os.path.expanduser('~/sleepdraw'))
sys.path.insert(0, SLEEPDRAW_ROOT)


def _seals():
    """Sleepdraw MCP, imported lazily so bank lookup, gap parsing, and tests
    work everywhere. Drafting fresh prompts needs it; bank hits don't."""
    try:
        import mcp_server as seals
        return seals
    except ImportError as e:
        raise RuntimeError(
            f'sleepdraw MCP unavailable (SLEEPDRAW_ROOT={SLEEPDRAW_ROOT}): {e}. '
            'Bank-reuse proposals still work; fresh seal drafting needs the MCP.') from e

BANK_REG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'art_bank', 'REGISTRY.json')


def bank_lookup(text):
    """Best bank entry for a gap's text, or None (draft fresh instead).

    Matches entry keywords + seal words; queued subjects count double
    (they were queued FOR these gaps). Pointers without keywords match on
    their seal line. Returns (entry, score). Never raises on a stale bank.
    """
    try:
        reg = json.load(open(BANK_REG, encoding='utf-8'))
    except (OSError, ValueError):
        return None, 0
    t = text.lower()
    best, best_score = None, 0
    for e in reg.get('entries', []):
        terms = list(e.get('keywords', []))
        terms += [w for w in re.findall(r'[a-z]{5,}', e.get('seal', '').lower())]
        score = sum(2 for k in terms if len(k.split()) > 1 and k.lower() in t)
        score += sum(1 for k in terms if len(k.split()) == 1 and
                     re.search(r'\b' + re.escape(k.lower()) + r'\b', t))
        if e.get('kind') == 'queued-subject':
            score *= 2
        if score > best_score:
            best, best_score = e, score
    return best, best_score


def white_gaps(timeline_md):
    """Block ids of WHITE (tone-break) holds, in order."""
    gaps = []
    for line in open(timeline_md, encoding='utf-8'):
        m = re.match(r'^(b\w+): WHITE', line.strip())
        if m:
            gaps.append(m.group(1))
    return gaps


def white_map_stuck(white_map_md, unit):
    """Stuck long-holds for one chapter from the lane white-map.

    White-map rows look like `| 17 | 36.0m | 11% | 212s@250, 152s@682 |`.
    Returns [(seconds, ref)] in row order; refs are estimator marks, not
    block ids — callers must NOT treat them as bids.
    """
    stuck = []
    try:
        lines = open(white_map_md, encoding='utf-8').read().splitlines()
    except OSError:
        return stuck
    for line in lines:
        m = re.match(r'^\|\s*0*(\d+)\s*\|[^|]*\|[^|]*\|\s*(.*?)\s*\|?\s*$', line)
        if not m or m.group(1) != str(int(unit)):
            continue
        for item in m.group(2).split(','):
            n = re.match(r'\s*(\d+)s@(\S+)', item or '')
            if n:
                stuck.append((int(n.group(1)), n.group(2)))
    return stuck


def propose(storyboard_json, timeline_md, out_path=None, white_map_md=None):
    sb = json.load(open(storyboard_json, encoding='utf-8'))
    blocks = {b['id']: b for b in sb['blocks']}
    lane_name, lane = for_path(storyboard_json)
    unit = lane.unit_id(storyboard_json)
    gaps = white_gaps(timeline_md)
    stuck = white_map_stuck(white_map_md, unit) if white_map_md else []
    priority = 'high' if any(s >= 120 for s, _ in stuck) else 'normal'
    proposals = {}
    for bid in gaps:
        b = blocks.get(bid)
        if b is None:
            continue
        nxt = [c for c in sb['blocks'] if c['id'] > bid]
        complete = nxt[0]['id'] if nxt else bid
        text = b.get('directed') or b.get('text', '')
        clean = re.sub(r'\[[^\]]*\]', '', text).strip()
        clean = re.sub(r'\s+', ' ', clean)
        hit, score = bank_lookup(clean)
        if hit is not None:
            seal_prompt_text = (
                f"[BANK {hit['id']}] {hit.get('seal', '')} — see "
                f"{hit.get('seal_brief', '')}; draft fresh only if the gap "
                f"needs more than the bank holds.")
            bank_ref = {'bank_id': hit['id'], 'bank_kind': hit['kind'],
                        'bank_status': hit['status'], 'match_score': score,
                        'brief': hit.get('seal_brief')}
            inv_sha = hit.get('preset_sha256')
            if inv_sha is None:
                try:
                    seals = _seals()
                    inv_sha = next((p['sha256'] for p in seals.presets()['presets']
                                    if p['preset'] == 'lora2-inv'), None)
                except RuntimeError:
                    inv_sha = None
        else:
            seals = _seals()
            inv_sha = next((p['sha256'] for p in seals.presets()['presets']
                            if p['preset'] == 'lora2-inv'), None)
            seal = seals.seal_prompt(clean, chapter=f'{lane_name}-{unit}')
            seal_prompt_text, bank_ref = seal['prompt'], None
        proposals[bid] = {
            'asset': None,
            'complete_bid': complete,
            'clear': 'fade',
            'fade': 1.5,
            'why': f"tone-break white at {bid} ({b.get('section', '')}): "
                    f"sealed art holds the breath — {(b.get('text', '')[:120])}",
            'sealed_prompt': seal_prompt_text,
            'preset': 'lora2-inv',
            'preset_sha256': inv_sha,
            'bank': bank_ref,
            'status': 'machine-proposed-unreviewed',
        }
    if out_path is None:
        # Staged in-factory, never in the series repo: promotion (copy to
        # the drops dir + render asset + write draws_chNN.json) is an
        # explicit owner/agent act. draws_for only reads exact-name
        # draws_chNN.json, so staged files can never render.
        stage = os.path.join(FACTORY_ROOT, 'projects', lane_name, 'proposed')
        os.makedirs(stage, exist_ok=True)
        out_path = os.path.join(stage, f'draws_ch{unit}.proposed.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'meta': {'lane': lane_name, 'unit': unit,
                            'priority': priority,
                            'white_map_stuck': [{'seconds': s, 'ref': r}
                                                for s, r in stuck],
                            'status': 'machine-proposed-unreviewed'},
                   'draws': proposals}, f, ensure_ascii=False, indent=1)
    return out_path, proposals


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--white-map')]
    wm = next((a.split('=', 1)[1] for a in sys.argv[1:]
               if a.startswith('--white-map=')), None)
    sb, tl = args[0], args[1]
    out = args[2] if len(args) > 3 else None
    path, props = propose(sb, tl, out, white_map_md=wm)
    print(f'{path}: {len(props)} proposed seals (asset:null until rendered + owner-promoted)')
