"""Tibetan-dead lane plugin: d01-d05 deaths of the Tibetan Book reading.

English-led with Sanskrit terms staying (IAST). Tibetan script banned by
owner order (same class as Nibbana no-Pali). Death toll opens every unit.
"""
import os
import re

NAME = 'tibetan-dead'


def match(sb_path):
    return '/tibetan-dead/' in sb_path and bool(re.search(r'storyboard_d\d+\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r'd(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def paths(repo, unit):
    lane_root = repo  # tibetan-dead repo root holds chapters/ directly
    return {'lane': 'tibetan-dead', 'ch': unit,
            'glossary': os.path.join(lane_root, f'glossary_d{unit}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_d{unit}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_d{unit}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_d{unit}.json')]}


def numeral_for(unit):
    return False  # deaths carry no on-screen numeral (owner may revise)


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    return None  # death ref stays spoken, never on screen (owner may revise)
