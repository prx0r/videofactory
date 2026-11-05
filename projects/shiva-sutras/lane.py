"""Shiva-sutras lane plugin: s00 intro + s01-s77 sutra units.

Units are sutras, not chapters: no chapter numerals anywhere in this
path. The intro header derives per-unit from the sutra ref (top-right)
and funny title (top-left), mirrored in house type.
"""
import os
import re

NAME = 'shiva-sutras'


def match(sb_path):
    return '/shiva/' in sb_path and bool(re.search(r'storyboard_s\d+\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r's(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '00').zfill(2)


def paths(repo, unit):
    lane_root = os.path.join(repo, 'shiva')
    return {'lane': 'shiva', 'ch': unit,
            'glossary': os.path.join(lane_root, f'glossary_s{unit}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_s{unit}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_s{unit}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_s{unit}.json')]}


def numeral_for(unit):
    return False  # sutras carry no chapter numeral


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    """Sutra ref (top-right) + funny title (top-left) from the unit itself:
    ref from the H1, title from the heading line."""
    ref, title = None, None
    for b in blocks:
        t = b.get('text', '').strip()
        if b.get('id') == 'b_opener':
            continue
        if b.get('type') == 'title' and ref is None:
            m = re.search(r'(\d+\.\d+)\s*$', t)
            if m:
                ref = m.group(1)
            continue
        if ref and title is None and b.get('type') == 'narration':
            m = re.match(r'^\d+\.\d+\s*—\s*(.+)$', t)
            if m:
                title = m.group(1).strip()
                break
    if not ref:
        return None
    return {'ref': ref, 'title': title or ''}
