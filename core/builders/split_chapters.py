#!/usr/bin/env python3
"""Split hed's chapter dump files into clean per-chapter markdown.
Usage: python3 split_chapters.py
Canonical: ch1<-tantrasara1, ch2<-tantrasara2, ch3-5<-tantrasara3-5,
ch6<-existing (verified identical), ch7-8<-tantrasara6-9, ch9-13<-tantrasara9-13,
ch14-18<-tantrasara14-18, ch19-22<-tantrasara19-22.
tantrasara3 (gmail chrome dump) is IGNORED per owner.
Strips: gmail headers, 'Keep reading'/'Next:' trailers, ' <domain> +1'
citation tails, standalone citation lines.
"""
import re, os, sys

SRC = '/home/ubuntu/kashmir_audio'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
OUT = os.path.join(_vf.repo_root(), 'chapters')

def clean(lines):
    out = []
    for l in lines:
        s = l.rstrip('\n')
        # standalone citation lines
        if re.match(r'^[a-z0-9_.-]+\.[a-z]+ \+1$', s.strip()) and len(s.strip().split()) <= 2:
            continue
        if s.strip() in ('Keep reading',):
            continue
        if re.match(r'^Next: Chapter \d+', s.strip()):
            continue
        # inline citation tails on description paragraphs
        s = re.sub(r'\s+(?:[a-z0-9_.-]+\.[a-z]+|TextGrid Repository|Sanskrit & Trika Shaivism|tylergneill\.github\.io) \+1$', '', s)
        # gmail chrome
        if re.match(r'^(Gmail|Skip to content|Using Gmail|.*screen readers|.*browser version|Inbox|Summarize|Prior Trades|To:|1 of \d+|\(no subject\))', s):
            continue
        out.append(s)
    # trim leading/trailing blanks
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out

def split_file(path):
    lines = open(path, encoding='utf-8').read().splitlines()
    chaps, cur, num = {}, [], None
    for l in lines:
        m = re.match(r'^Tantrasāra — Chapter (\d+)\s*$', l)
        if m:
            if cur and num:
                chaps[num] = cur
            num, cur = int(m.group(1)), [l]
        elif num is not None:
            cur.append(l)
    if cur and num:
        chaps[num] = cur
    return chaps

JOBS = [
    ('tantrasara1', [1]), ('tantrasara2', [2]), ('tantrasara3-5', [3, 4, 5]),
    ('tantrasara6-9', [7, 8]), ('tantrasara9-13', [9, 10, 11, 12, 13]),
    ('tantrasara14-18', [14, 15, 16, 17, 18]),
    ('tantrasara19-22', [19, 20, 21, 22]),
]
def main():
    os.makedirs(OUT, exist_ok=True)
    for fname, want in JOBS:
        chaps = split_file(f'{SRC}/{fname}')
        for n in want:
            assert n in chaps, f'ch{n} missing from {fname} (has {sorted(chaps)})'
            body = clean(chaps[n])
            head = f'# Tantrasāra — Chapter {n}\n\n'
            text = head + '\n'.join(body) + '\n'
            # ch6 exists already (verified identical source); never overwrite it
            if n == 6:
                continue
            with open(f'{OUT}/ch{n:02d}.md', 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'ch{n:02d}: {len(text.split())} words from {fname}')


if __name__ == '__main__':
    main()