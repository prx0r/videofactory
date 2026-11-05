#!/usr/bin/env python3
"""Write a complete storyboard-order *plan*, not measured video timings.

Usage: python3 holds_timeline.py <storyboard.json> <glossary.json> <out.md>
All blocks are visited. Each occurrence uses the video builder's whitespace
tokenization; repeated mentions are shown, including proposed terms that
currently play over white. Actual render metadata and frames remain the
authority for timed card changes.
"""
import json
import re
import sys
import unicodedata


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower())
                   if unicodedata.category(c) != 'Mn')


def main():
    sb = json.load(open(sys.argv[1], encoding='utf-8'))
    gl = json.load(open(sys.argv[2], encoding='utf-8'))
    lines = ['# Holds timeline — planning view', '',
             'Complete storyboard-order event and term-mention plan; times are not measured.',
             'Confirmed mentions can appear as cards. Proposed mentions remain white.',
             'Use video metadata and proof frames to judge actual onsets and persistence.', '']
    count = 0
    previous_section = None
    for b in sb['blocks']:
        if b['id'] == 'b_opener':
            lines.append('b_opener: thumbnail / opener')
            continue
        if previous_section is not None and b['section'] != previous_section:
            lines.append(f"{b['id']}: SECTION CHANGE")
        previous_section = b['section']
        if b['type'] in ('verse', 'title', 'figure'):
            lines.append(f"{b['id']}: {b['type'].upper()} — {b['text'][:80].strip()}")
        if b['type'] == 'dialogue' or b.get('directed', '').startswith('[long pause]'):
            lines.append(f"{b['id']}: TONE BREAK")
        if b['type'] not in ('narration', 'dialogue'):
            continue
        words = [w for w in b['text'].strip().split() if re.search(r'\w', w, re.U)]
        for i, word in enumerate(words, 1):
            key = fold(word.strip('.,!?;:\'"—-'))
            if key not in gl:
                continue
            term = gl[key]
            state = 'CONFIRMED' if term['status'] == 'confirmed' else 'PROPOSED — white'
            lines.append(f"{b['id']} word {i}: TERM {key} ({term['deva']} — {term['gloss']}) [{state}]")
            count += 1
    with open(sys.argv[3], 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'wrote {sys.argv[3]} ({len(sb["blocks"])} blocks visited, {count} term mentions)')


if __name__ == '__main__':
    main()
