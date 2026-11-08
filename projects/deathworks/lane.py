"""Deathworks lane plugin: five standalone death pieces.

Units are w01-w05 mapped to work slugs (heist, escape, rebirth, madman,
ancestors). Sanskrit stays where present (IAST/Deva); English-led.
"""
import os
import re

NAME = 'deathworks'

SLUGS = ['heist', 'escape', 'rebirth', 'madman', 'ancestors']


def _slug(unit):
    m = re.search(r'(\d+)', unit or '')
    i = int(m.group(1)) - 1 if m else 0
    return SLUGS[max(0, min(i, len(SLUGS) - 1))]


def match(sb_path):
    return '/deathworks/' in sb_path and bool(re.search(r'storyboard_(heist|escape|rebirth|madman|ancestors)\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r'storyboard_(heist|escape|rebirth|madman|ancestors)\.json$', os.path.basename(sb_path))
    if not m:
        return '01'
    return '%02d' % (SLUGS.index(m.group(1)) + 1)


def paths(repo, unit):
    lane_root = repo  # deathworks repo root holds chapters/ directly
    slug = _slug(unit)
    return {'lane': 'deathworks', 'ch': slug,
            'glossary': os.path.join(lane_root, f'glossary_{slug}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_{slug}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_{slug}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_{slug}.json')]}


def numeral_for(unit):
    return False  # pieces carry no on-screen numeral (owner may revise)


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    return None  # refs stay spoken, never on screen (owner may revise)
