"""Entry-gate helper: fail-closed by default.

VF_GATES=strict (default): any gate failure raises, stopping the stage.
VF_GATES=compat (migration escape hatch only): failures are logged loudly
and the run continues — every compat pass is technical debt listed by
check.py. Compat exists only for parity dry-runs against frozen data;
production renders must run strict. The mode is explicit and logged;
it is never silent.
"""
import os


def mode():
    return os.environ.get('VF_GATES', 'strict')


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


def advisory(stage, name, fn, *args, **kwargs):
    """Owner order 2026-11-06: once the storyboard is green, NOTHING else
    may hold a render up. Advisory checks still run and print their verdict
    (so defects stay visible and recorded), but they never raise and never
    stop the line — the storyboard gate is the one gate that decides."""
    try:
        out = fn(*args, **kwargs)
        print(f'gate {stage}/{name}: PASS (advisory)', flush=True)
        return out
    except Exception as e:
        print(f'gate {stage}/{name}: ADVISORY-FAIL ({e}) — not blocking '
              f'(storyboard green is the only render gate)', flush=True)
        return None
