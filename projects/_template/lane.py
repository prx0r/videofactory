"""Starter lane plugin for a new project. Fill the TODOs, keep the signatures.

The engine calls: match(sb_path) -> unit_id(sb_path) -> paths(repo, unit),
plus numeral_for / title_for / header for the intro bug. See
projects/tantrasara/lane.py (chapters) and projects/shiva-sutras/lane.py
(sutras, no numerals) as the two worked examples.
"""
import os
import re

NAME = '_template'


def match(sb_path):
    # TODO: return True for this project's storyboard paths, e.g.:
    # return '/myproj/' in sb_path and sb_path.endswith('.json')
    return False


def unit_id(sb_path):
    # TODO: extract the zero-padded unit id, e.g. '07'
    m = re.search(r'u(\d+)\.json$', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def paths(repo, unit):
    # TODO: point at this project's files. Keys are the whole contract —
    # keep every key, change only the values.
    return {'lane': NAME, 'ch': unit,
            'glossary': os.path.join(repo, f'glossary_u{unit}.json'),
            'verse': os.path.join(repo, f'verse_gloss_u{unit}.json'),
            'assets': os.path.join(repo, 'assets', 'thumbnail'),
            'thumbbox': (1400, 730), 'numeral': unit, 'art_center': False,
            'drops': os.path.join(repo, f'drops_u{unit}.json'),
            'storyboards': [os.path.join(repo, f'storyboard_u{unit}.json')]}


def numeral_for(unit):
    return unit  # TODO: False if units carry no numeral (shiva pattern)


def title_for(blocks, glossary=None):
    import holds as _H
    return _H.chapter_title(blocks, glossary)


def header(blocks, glossary=None):
    return None  # TODO: {'ref': ..., 'title': ...} for ref-style headers
