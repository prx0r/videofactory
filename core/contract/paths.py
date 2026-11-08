"""Central path resolution for the video factory.

Every builder resolves series locations through these helpers — never a
hardcoded home path. Defaults are byte-identical to the frozen tantrasara
system, so default behavior is parity by construction; lanes override via
environment (drivers set these from series/*.json).
"""
import os

DEFAULTS = {
    'VF_REPO': '~/tantrasara',
    'VF_RENDERS': '~/vol/tantrasara/renders',
    'VF_R2': 'r2:svread-audio/tantrasara',
    'VF_SERIES': 'tantrasara',
}


def repo_root():
    return os.path.expanduser(os.environ.get('VF_REPO', DEFAULTS['VF_REPO']))


def renders_root():
    return os.path.expanduser(os.environ.get('VF_RENDERS', DEFAULTS['VF_RENDERS']))


def r2_prefix():
    return os.environ.get('VF_R2', DEFAULTS['VF_R2']).rstrip('/')


def series_name():
    return os.environ.get('VF_SERIES', DEFAULTS['VF_SERIES'])


def contract_dir():
    return os.path.dirname(os.path.abspath(__file__))


def builders_dir():
    return os.path.join(os.path.dirname(contract_dir()), 'builders')


def projects_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'projects')


def _series_cfg():
    """Project lane config (projects/<name>/project.json); missing = {}. Never raises."""
    import json as _j
    try:
        return _j.load(open(os.path.join(projects_dir(), series_name(), 'project.json'), encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def apply_series(name):
    """Point every downstream path at a lane config (drivers call this from
    --series before spawning builders; subprocesses inherit the env)."""
    import json as _j
    cfg = _j.load(open(os.path.join(projects_dir(), name, 'project.json'), encoding='utf-8'))
    os.environ['VF_SERIES'] = cfg.get('series', name)
    os.environ['VF_REPO'] = cfg.get('repo', DEFAULTS['VF_REPO'])
    os.environ['VF_RENDERS'] = cfg.get('renders', DEFAULTS['VF_RENDERS'])
    os.environ['VF_R2'] = cfg.get('r2', DEFAULTS['VF_R2'])
    return cfg


def voices():
    """Seat voice IDs: series config wins, frozen IDs are the fallback."""
    cfg = _series_cfg()
    v = cfg.get('voices', {})
    return {
        'granny': v.get('granny', '614f8afd83f841048c040b2c6234d2c1'),
        'man': v.get('man', 'fcfd5ebf496949ed9f76b3a533ee4738'),
        'verse': v.get('verse', '4e873c37d4cb439e9bccc4dc1f633290'),
        'roadman': v.get('roadman', 'e64e97ef91304e2894cd72ff03b86d97'),
    }


def fonts():
    """Typography faces: env wins (VF_FONTS dir), frozen faces are default."""
    base = os.environ.get('VF_FONTS', os.path.expanduser('~/.fonts'))
    return {
        'deva': os.path.join(base, 'TiroDevanagariSanskrit-Regular.ttf'),
        'gloss': os.path.join(base, 'CormorantGaramond-Italic.ttf'),
        'subtitle': os.path.join(base, 'CormorantGaramond-Medium.ttf'),
    }


def phoneme_dir():
    return os.path.expanduser(os.environ.get('VF_PHONEMES', '~/deitybody/site/audio/phonemes'))


def tts_script():
    return os.path.expanduser(os.environ.get('VF_TTS', '~/shiva-sutras/tools/tts_line.py'))


def bell():
    return os.path.expanduser(os.environ.get('VF_BELL', '~/vatulanatha/sfx/bell_ding.wav'))
