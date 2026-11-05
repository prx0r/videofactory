#!/usr/bin/env python3
"""Scaffold a new series lane (NEW-LANE pattern, uniform layout).

Usage: python3 new_series.py <name> --units 10 [--repo ~/series-<name>] [--r2 r2:svread-audio/<name>]

Creates the lane skeleton + config + intake log. Data (unit md files) is
authored next per docs/UNITS.md, then the normal chain takes over.
Builders stay single-copy; only lane paths are yours.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith('-'):
        sys.exit('usage: new_series.py <name> --units 10 [--repo PATH] [--r2 PREFIX]')
    name = a[0]
    units = int(a[a.index('--units') + 1]) if '--units' in a else 10
    repo = os.path.expanduser(a[a.index('--repo') + 1]) if '--repo' in a else os.path.expanduser(f'~/{name}')
    r2 = a[a.index('--r2') + 1] if '--r2' in a else f'r2:svread-audio/{name}'
    for d in ('units', 'storyboards', 'review', os.path.join('assets', 'thumbnail'), 'casting'):
        os.makedirs(os.path.join(repo, d), exist_ok=True)
    cfg = {
        'series': name,
        'repo': repo,
        'renders': os.path.expanduser(f'~/vol/{name}/renders'),
        'r2': r2,
        'review_r2': r2 + '/review',
        'unit_scheme': 'uNN',
        'unit_target': units,
        'note': 'Fill units/uNN-slug.md per docs/UNITS.md, then storyboard each.',
    }
    cfg_path = os.path.join(ROOT, 'series', f'{name}.json')
    json.dump(cfg, open(cfg_path, 'w'), indent=1)
    intake = os.path.join(repo, 'INTAKE.md')
    if not os.path.exists(intake):
        open(intake, 'w').write(
            f'# INTAKE — {name} (scaffolded)\n\nUnits target: {units} (UNITS.md).\n\n'
            '## Unit list (one line each: id, source span, why-it-earns-its-film)\n\n'
            '## Decisions + unsure list (owner disposes)\n\n'
            '## Next: storyboard unit 01 → gate → sheets → publish → approval\n')
    print(f'lane {name}: skeleton at {repo}, config at {cfg_path}')
    print(f'next: author units/u01-*.md per docs/UNITS.md, then build_storyboard.py')


if __name__ == '__main__':
    main()
