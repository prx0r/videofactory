#!/usr/bin/env python3
"""Propose sleepdraw seals for white-hold art gaps (machine-proposed, owner disposes).

Reads a holds timeline (review/chNN/timeline.md, WHITE entries) + the chapter
storyboard, drafts one hermetic seal prompt per gap via sleepdraw's
mcp_server.seal_prompt, and writes draws_chNN.proposed.json beside the drops
file. The proposed file NEVER renders (draws_for matches draws_chNN.json
exactly). Owner promotes: render each asset (sleepdraw MCP render_seal with
explicit confirm_paid), then write draws_chNN.json {start_bid: {asset,
complete_bid, clear, fade, why}} — draws_for fails loud on missing fields.

Usage: python3 propose_draws.py <storyboard.json> <timeline.md> [out.json]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from lane_api import for_path  # noqa: E402

SLEEPDRAW_ROOT = os.environ.get('SLEEPDRAW_ROOT', '/root/sleepdraw')
sys.path.insert(0, SLEEPDRAW_ROOT)
import mcp_server as seals  # noqa: E402 (pure seal_prompt; paid render stays behind confirm_paid)

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


def propose(storyboard_json, timeline_md, out_path=None):
    sb = json.load(open(storyboard_json, encoding='utf-8'))
    blocks = {b['id']: b for b in sb['blocks']}
    lane_name, lane = for_path(storyboard_json)
    unit = lane.unit_id(storyboard_json)
    gaps = white_gaps(timeline_md)
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
        inv_sha = next((p['sha256'] for p in seals.presets()['presets']
                        if p['preset'] == 'lora2-inv'), None)
        if hit is not None:
            seal_prompt_text = (
                f"[BANK {hit['id']}] {hit.get('seal', '')} — see "
                f"{hit.get('seal_brief', '')}; draft fresh only if the gap "
                f"needs more than the bank holds.")
            bank_ref = {'bank_id': hit['id'], 'bank_kind': hit['kind'],
                        'bank_status': hit['status'], 'match_score': score,
                        'brief': hit.get('seal_brief')}
        else:
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
        lane_paths = lane.paths(os.path.dirname(os.path.abspath(storyboard_json)), unit)
        stem = os.path.basename(lane_paths['drops']).replace('drops_', 'draws_')
        out_path = os.path.join(os.path.dirname(lane_paths['drops']),
                                stem.replace('.json', '.proposed.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(proposals, f, ensure_ascii=False, indent=1)
    return out_path, proposals


if __name__ == '__main__':
    sb, tl = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    path, props = propose(sb, tl, out)
    print(f'{path}: {len(props)} proposed seals (asset:null until rendered + owner-promoted)')
