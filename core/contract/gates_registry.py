#!/usr/bin/env python3
"""Versioned gate registry (qp_gates pattern on a qprivately kernel idea).

Every gate is a pure predicate with a versioned id: same inputs ALWAYS give
the same verdict. New logic means a new gate id — never a silent edit.
Cognition (builders, skills, agents) is untrusted; truth enters only through
these gates on evidence; authority (owner bless/waiver) is an explicit grant
(approved_*.json, *.waivers.json), never implied.

Run `python3 gates_registry.py --list` to audit the registry.
"""
import sys

REGISTRY = {
    # entry gates (run before spending)
    'video/bundle-v1': ('factory_contract', 'validate_bundle'),
    'video/review-pack-v1': ('factory_contract', 'require_current_review_pack'),
    'video/source-v1': ('factory_contract', 'verify_storyboard_source'),
    'video/storyboard-gate-v1': ('factory_contract', 'require_storyboard_gate'),
    'video/audio-complete-v1': ('factory_contract', 'require_audio_complete'),
    # v2: rewritten 2026-11-06 to mirror renderer runs (was: all cue-order
    # 5-windows, which flagged stacks that never co-occur — false positive
    # on ch19). v1 retired, never edited.
    'video/list-geometry-v2': ('factory_contract', 'require_list_geometry'),
    # advisory in ship mode (renderer caps persists at 60s by law; H4 + ears
    # dispose). Still a versioned gate so the rule change is visible.
    'video/hold-scan-v1-advisory': ('factory_contract', 'require_hold_scan'),
    'video/issues-clear-v1': ('factory_contract', 'require_issues_clear'),
    # data discipline (baked into validate_bundle + schemas)
    'glossary/no-empty-confirmed-v1': ('factory_contract', 'validate_bundle'),
    'glossary/no-machine-deva-v2': ('factory_contract', 'validate_bundle'),
    # ship gates (independent validator, measured artifacts only)
    'ship/verified-v1': ('factory_contract', 'require_verified_video'),
    'ship/max-white-span-v1': ('validate_ship', 'criterion_max_white_span'),
    'ship/geometry-proven-v1': ('validate_ship', 'criterion_geometry_proven'),
    'ship/review-current-v1': ('factory_contract', 'require_current_review_pack'),
    'ship/ears-v1': ('factory_contract', 'require_owner_ears'),
}


def resolve(gate_id):
    import importlib
    import os as _os
    import sys as _sys
    if gate_id not in REGISTRY:
        raise KeyError(f'unknown gate: {gate_id} (new logic needs a new registered id)')
    _here = _os.path.dirname(_os.path.abspath(__file__))
    for _p in (_here, _os.path.join(_here, '..', 'builders'), _os.path.join(_here, '..')):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    mod_name, func_name = REGISTRY[gate_id]
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, func_name)
    if not callable(fn):
        raise TypeError(f'gate {gate_id} does not resolve to a callable')
    return fn


def main():
    if '--list' not in sys.argv:
        print(__doc__)
        print('usage: python3 gates_registry.py --list')
        return 2
    ok = True
    for gate_id in sorted(REGISTRY):
        try:
            resolve(gate_id)
            print(f'PASS {gate_id} -> {".".join(REGISTRY[gate_id])}')
        except (KeyError, TypeError, ImportError) as e:
            ok = False
            print(f'FAIL {gate_id}: {e}')
    print('GATES ' + ('GREEN' if ok else 'RED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
