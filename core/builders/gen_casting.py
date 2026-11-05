#!/usr/bin/env python3
"""Casting sheets: every quote needing a human man/granny call, with context.
Usage: python3 gen_casting.py
Reads chapters/chNN.md, writes casting/cast_chNN.md (UNCAST blocks only).
Owner marks each M (man) or G (granny); engineer encodes to overrides.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import json, os, subprocess, sys

BASE = _vf.repo_root()
os.makedirs(f'{BASE}/casting', exist_ok=True)

def blocks_for(ch):
    subprocess.run(['python3', f'{BASE}/build_storyboard.py',
                    f'{BASE}/chapters/ch{ch}.md', f'/tmp/sb_{ch}.json'],
                   capture_output=True, text=True)
    return json.load(open(f'/tmp/sb_{ch}.json'))['blocks']

for ch in ['02', '03', '04', '05', '07', '08', '09', '10', '11', '12', '13',
           '14', '15', '16', '17', '18', '19', '20', '21', '22']:
    blocks = blocks_for(ch)
    byid = {b['id']: i for i, b in enumerate(blocks)}
    uncast = [b for b in blocks if b['voice'] == 'UNCAST']
    auto_man = [b for b in blocks if b['type'] == 'dialogue' and b['voice'] == 'man']
    lines = [f'# Casting — chapter {ch}', '',
             f'{len(uncast)} quotes need a call. Mark each `M` (man) or `G` (granny).',
             f'{len(auto_man)} already man via the Abhinava rule (listed at end for veto).', '']
    for b in uncast:
        i = byid[b['id']]
        prev = next((x['text'][:100] for x in reversed(blocks[:i]) if x['type'] == 'narration'), '—')
        nxt = next((x['text'][:100] for x in blocks[i + 1:i + 4] if x['type'] == 'narration'), '—')
        lines += [f"## {b['id']} · [{b['section'][:45]}]", '', f'> {b["text"]}', '',
                  f'before: {prev}', '', f'after: {nxt}', '', 'call: _', '']
    lines += ['---', '## Auto-man (veto with X)', '']
    for b in auto_man:
        lines.append(f"- {b['id']}: {b['text'][:80]}")
    open(f'{BASE}/casting/cast_ch{ch}.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'ch{ch}: {len(uncast)} calls, {len(auto_man)} auto-man')
