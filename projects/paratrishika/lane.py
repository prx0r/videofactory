"""Paratrishika lane plugin: v01-v36 parts of the slang reading.

Units are sequential parts (I-XXXVI from two exports, joined at the XXIX
resume point). Sanskrit lane: verse voice chants Deva/IAST natively.
"""
import os
import re

NAME = 'paratrishika'


def match(sb_path):
    return '/paratrishika/' in sb_path and bool(re.search(r'storyboard_v\d+\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r'v(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def paths(repo, unit):
    lane_root = repo  # paratrishika repo root holds chapters/ directly
    digits = re.sub(r'\D', '', unit).zfill(2)
    return {'lane': 'paratrishika', 'ch': digits,
            'glossary': os.path.join(lane_root, f'glossary_v{digits}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_v{digits}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_v{digits}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_v{digits}.json')]}


def numeral_for(unit):
    return False  # parts carry no on-screen numeral (owner may revise)


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    return None  # refs stay spoken, never on screen (owner may revise)
