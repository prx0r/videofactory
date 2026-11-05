"""Entry-gate helper: strictness with a migration bridge.

VF_GATES=strict (target): any gate failure raises, stopping the stage.
VF_GATES=compat (default during migration): failures are logged loudly and
the run continues — every compat pass is technical debt listed by check.py.
The mode is explicit and logged; it is never silent.
"""
import os


def mode():
    return os.environ.get('VF_GATES', 'compat')


def entry_check(stage, name, fn, *args, **kwargs):
    """Run a contract gate fn; raise in strict mode, log loudly in compat."""
    try:
        out = fn(*args, **kwargs)
        print(f'gate {stage}/{name}: PASS', flush=True)
        return out
    except Exception as e:
        print(f'gate {stage}/{name}: FAIL ({e}) [mode={mode()}]', flush=True)
        if mode() == 'strict':
            raise
        return None
