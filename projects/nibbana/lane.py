"""Nibbana lane plugin: n01-n10 chapters of the Mind Stilled reading.

Units are chapters (~3 sermons each), English-only by owner order
(no Pali anywhere: no diacritics, no headwords, English glossary only).
Sutta/prose quotes voice as narration; skeptic and patient voices go man.
"""
import os
import re

NAME = 'nibbana'


def match(sb_path):
    return '/nibbana/' in sb_path and bool(re.search(r'storyboard_n\d+\.json$', sb_path))


def unit_id(sb_path):
    m = re.search(r'n(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def paths(repo, unit):
    lane_root = repo  # nibbana repo root holds chapters/ directly
    return {'lane': 'nibbana', 'ch': unit,
            'glossary': os.path.join(lane_root, f'glossary_n{unit}.json'),
            'verse': os.path.join(lane_root, f'verse_gloss_n{unit}.json'),
            'assets': os.path.join(lane_root, 'assets', 'thumbnail'),
            'thumbbox': (760, 760), 'numeral': False, 'art_center': True,
            'drops': os.path.join(lane_root, f'drops_n{unit}.json'),
            'storyboards': [os.path.join(lane_root, 'storyboards', f'storyboard_n{unit}.json')]}


def numeral_for(unit):
    return False  # chapters carry no on-screen numeral (owner may revise)


def title_for(blocks, glossary=None):
    return None


def header(blocks, glossary=None):
    return None  # sermon refs stay spoken, never on screen (owner may revise)
