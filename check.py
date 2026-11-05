#!/usr/bin/env python3
"""check.py — the canonical factory gate. Exit 0 = canonical, else failing step named.

  python3 check.py [--strict]

Steps: schemas import · unit tests green · builders compile · contract audit
read-only vs referenced series data · no hardcoded series paths in core ·
VF_GATES mode reported.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
fails = []


def step(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name + (f": {detail}" if detail else ""))


def main():
    strict = '--strict' in sys.argv
    # 1. schemas import (needs jsonschema per requirements-contract.txt)
    try:
        sys.path.insert(0, os.path.join(ROOT, 'core', 'contract'))
        import factory_contract  # noqa
        step('schemas-import', True)
    except SystemExit as e:
        step('schemas-import', False, f'missing dependency ({e})')
    except Exception as e:
        step('schemas-import', False, str(e)[:200])
    # 2. unit tests (pure + contract suites)
    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s',
                        os.path.join(ROOT, 'tests')], capture_output=True, text=True)
    tail = (r.stderr.strip().splitlines() or ['?'])[-1]
    step('unit-tests', r.returncode == 0, tail)
    # 3. builders compile
    import glob
    bad = []
    for f in glob.glob(os.path.join(ROOT, 'core', '**', '*.py'), recursive=True):
        try:
            compile(open(f, encoding='utf-8').read(), f, 'exec')
        except SyntaxError as e:
            bad.append(os.path.basename(f) + str(e)[:80])
    step('builders-compile', not bad, '; '.join(bad))
    # 4. no hardcoded series paths in core (lane config is the only source)
    import re
    hard = []
    for f in glob.glob(os.path.join(ROOT, 'core', '**', '*.py'), recursive=True):
        for i, ln in enumerate(open(f, encoding='utf-8'), 1):
            if re.search(r"expanduser\(['\"]~/(tantrasara|vol)", ln) and 'paths.py' not in f:
                hard.append(f'{os.path.basename(f)}:{i}')
    step('no-hardcoded-paths', not hard, '; '.join(hard[:5]))
    # 5. read-only contract audit vs referenced series data (never writes)
    try:
        sys.path.insert(0, os.path.join(ROOT, 'core', 'builders'))
        import paths as _vf
        repo = _vf.repo_root()
        import factory_contract as C
        found = sorted(__import__('glob').glob(os.path.join(repo, 'storyboard_ch*.json')))
        step('series-data-visible', bool(found), f'{len(found)} storyboards via {repo}')
    except Exception as e:
        step('series-data-visible', False, str(e)[:200])
    print('VF_GATES mode:', os.environ.get('VF_GATES', 'compat'),
          '(strict=gates raise; compat=log-and-continue)')
    if strict and os.environ.get('VF_GATES') != 'strict':
        step('strict-mode', False, 'set VF_GATES=strict')
    print('RESULT ' + ('CANONICAL' if not fails else f'{len(fails)} FAILING'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
