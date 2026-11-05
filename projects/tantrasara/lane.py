"""Tantrasara lane plugin: 22 chapters, numeral + canonical title header."""
import os
import re

NAME = 'tantrasara'


def match(sb_path):
    base = os.path.basename(sb_path)
    return bool(re.search(r'storyboard_ch\d+\.json$', base)) and '/shiva/' not in sb_path


def unit_id(sb_path):
    m = re.search(r'ch(\d+)', os.path.basename(sb_path))
    return (m.group(1) if m else '01').zfill(2)


def _storyboard(repo, unit):
    cands = [os.path.join(repo, f'storyboard_ch{unit}.json')]
    if unit == '06':
        cands.append(os.path.join(repo, 'storyboard_ch6.json'))  # legacy stem
    return cands


def paths(repo, unit):
    return {'lane': 'tantrasara', 'ch': unit,
            'glossary': os.path.join(repo, f'glossary_ch{unit}.json'),
            'verse': os.path.join(repo, f'verse_gloss_ch{unit}.json'),
            'assets': None, 'thumbbox': (1400, 730), 'numeral': None,
            'art_center': False,
            'drops': os.path.join(repo, f'drops_ch{unit}.json'),
            'storyboards': _storyboard(repo, unit)}


def numeral_for(unit):
    return unit  # zero-padded chapter numeral, top-right


def title_for(blocks, glossary=None):
    import holds as _H
    return _H.chapter_title(blocks, glossary)


def header(blocks, glossary=None):
    return None  # tantrasara header is numeral + title, not a ref block
