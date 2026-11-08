"""Paramarthasara lane plugin: p01-p07 parts of the slang reading.

Units are 15-verse parts. Sanskrit lane: verse voice chants Deva/IAST
natively; term cards need citation Deva + final gloss, confirmed-only.
"""
import os
import re

NAME = 'paramarthasara'


def match(sb_path):
    return '/paramarthasara/' in sb_path and bool(re.search(r'storyboard_p\d+\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r'p(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def paths(repo, unit):
    lane_root = repo  # paramarthasara repo root holds chapters/ directly
    return {'lane': 'paramarthasara', 'ch': unit,
            'glossary': os.path.join(lane_root, f'glossary_p{unit}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_p{unit}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_p{unit}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_p{unit}.json')]}


def numeral_for(unit):
    return False  # parts carry no on-screen numeral (owner may revise)


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    return None  # verse refs stay spoken, never on screen (owner may revise)
