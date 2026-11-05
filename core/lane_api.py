"""Lane plugin interface: engine stays generic, projects own their specifics.

A lane is a directory under projects/ with:
  project.json  unit scheme, match marks, path templates, voices, R2
  lane.py       match(sb_path), unit_id(sb_path), paths(repo, unit),
                header(blocks, glossary)

The dispatcher (for_path) picks the lane by VF_PROJECT override first,
then by path marks. holds.lane_for() delegates here and keeps its dict
shape, so builders never touch lane internals.
"""
import importlib.util
import os

FACTORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def projects_dir():
    return os.path.join(FACTORY_ROOT, 'projects')


def load_lane(name):
    mod_path = os.path.join(projects_dir(), name, 'lane.py')
    if not os.path.exists(mod_path):
        raise ValueError(f'unknown project lane: {name}')
    spec = importlib.util.spec_from_file_location(f'vf_lane_{name}', mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def for_path(sb_path):
    """(lane_name, lane_module) for a storyboard path."""
    forced = os.environ.get('VF_PROJECT')
    if forced:
        return forced, load_lane(forced)
    ap = os.path.abspath(sb_path)
    for name in sorted(os.listdir(projects_dir())):
        if name.startswith('_'):
            continue
        try:
            mod = load_lane(name)
        except ValueError:
            continue
        try:
            if mod.match(ap):
                return name, mod
        except Exception:
            continue
    raise ValueError(f'no project lane matches {sb_path} (set VF_PROJECT to force one)')


def intro_args(sb_path, blocks, glossary=None):
    """Intro bug arguments from the lane plugin: title entry, header
    block (or None), numeral semantics. Callers pass these straight to
    holds.intro_hold — no series conditionals in builders."""
    name, mod = for_path(sb_path)
    unit = mod.unit_id(sb_path)
    return {'ch': unit,
            'title': mod.title_for(blocks, glossary),
            'header': mod.header(blocks, glossary),
            'numeral': mod.numeral_for(unit)}
