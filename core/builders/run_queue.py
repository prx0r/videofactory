#!/usr/bin/env python3
"""Inspect or start one production job without guessing its state.

--refresh is read/derive-only with respect to production; --run-next is the
explicit launch action. Pending reviews and failures require --resume CH.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf

from factory_contract import (ContractError, read_json, require_current_review_pack, require_issues_clear,
                              require_verified_video, require_voice_energy, validate_bundle,
                              video_build_lock, video_lock_holder)
from proof_contract import require_reviewed_assembly
from qwen_review import require_disposition

BASE = Path(_vf.repo_root())
REG = BASE / 'REGISTRY.json'
QUEUE_LOCK = Path('/tmp/tantrasara_queue.lock')
FINALS_DIR = Path(_vf.renders_root()) / 'finals'  # mockable: hermetic tests point it at fixtures


def load_registry():
    if not Path(REG).exists():
        return {'tantrasara': {f'{i:02d}': {} for i in range(1, 23)},
                'queue': [], 'processes': {}, 'locks': {}}
    value = read_json(REG)
    if not isinstance(value, dict) or not isinstance(value.get('tantrasara'), dict):
        raise ContractError('REGISTRY.json needs a tantrasara object')
    return value


def save_registry(reg):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=Path(REG).parent, delete=False) as f:
        json.dump(reg, f, indent=2)
        temp = f.name
    os.replace(temp, REG)


def refresh(reg):
    """Derive readiness from artifacts; preserve unresolved active/failed work."""
    for ch, st in reg.get('tantrasara', {}).items():
        if not isinstance(st, dict) or not re.fullmatch(r'0[1-9]|1[0-9]|2[0-2]', ch):
            continue
        if st.get('stage') == 'rendering':
            try:
                log = Path(st['log']).read_text(encoding='utf-8', errors='replace')
            except (OSError, KeyError):
                log = ''
            if 'RUN_ALL_RESULT=PENDING_REVIEW' in log:
                st['stage'] = 'pending-review'
                pending = re.findall(r'"([a-z-]+)"\s*:\s*"PENDING_REVIEW"', log)
                st['resume_from'] = pending[-1] if pending else 'video'
                continue
            if 'RUN_ALL_RESULT=FAILED' in log or 'Traceback' in log:
                st['stage'] = 'failed'
                continue
            if 'RUN_ALL_RESULT=OK' not in log:
                # Process may be alive, killed, or detached: never promote an
                # unknown run to ready just because its PID disappeared.
                continue
        if st.get('stage') in ('pending-review', 'failed'):
            continue
        video = FINALS_DIR / f'ch{ch}_full.mp4'
        sb = BASE / ('storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json')
        man_ok = ap_ok = False
        try:
            require_current_review_pack(sb)
            man_ok = True
        except (OSError, ContractError):
            pass
        try:
            validate_bundle(sb, require_approval=True)
            ap_ok = True
        except (OSError, ContractError):
            pass
        video_ok = False
        if video.exists() and ap_ok:
            try:
                require_reviewed_assembly(sb, video)
                require_verified_video(sb, video)
                require_voice_energy(sb, video)
                require_disposition(sb, video)
                video_ok = True
            except (OSError, ContractError):
                pass
        # Issues are a WORK LIST, never a blocker (owner order 2026-11-06:
        # after the storyboard passes, nothing holds a render up). The
        # checker's findings are attached as data; --run-next launches.
        issues_note = ''
        issues_path = FINALS_DIR.parent / 'issues' / f"{'ch6' if ch == '06' else 'ch' + ch}.issues.json"
        if issues_path.exists():
            try:
                require_issues_clear(sb, issues_path.parent)
            except ContractError as _ie:
                issues_note = str(_ie)[:200]
        if video_ok:
            st['stage'] = 'rendered-awaiting-ears'
        elif video.exists():
            st['stage'] = 'video-needs-review'
        elif ap_ok:
            # approval (the owner act) is what makes a unit ready. Review
            # packs and issue files are records, never readiness gates
            # (owner order 2026-11-06).
            st['stage'] = 'approved-ready'
        elif man_ok:
            st['stage'] = 'review-published'
        else:
            st['stage'] = 'needs-review'
        st['unverified_video_present'] = video.exists() and not video_ok
    return reg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--run-next', action='store_true')
    parser.add_argument('--resume', metavar='CH', help='make a reviewed or failed chapter eligible for an explicit retry')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    with video_build_lock(QUEUE_LOCK):
        reg = load_registry()
        if args.refresh:
            refresh(reg)
            print('board refreshed from current artifacts')
        if args.resume:
            ch = args.resume.zfill(2)
            if not re.fullmatch(r'0[1-9]|1[0-9]|2[0-2]', ch):
                parser.error('--resume must name a chapter from 01 to 22')
            st = reg['tantrasara'].get(ch)
            if not isinstance(st, dict) or st.get('stage') not in ('pending-review', 'failed', 'video-needs-review', 'needs-issues'):
                raise ContractError(f'ch{ch} has no stopped job to resume')
            sb = BASE / ('storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json')
            validate_bundle(sb, require_approval=True)
            # storyboard+approval is the gate; review pack / issues are
            # recording only (owner order 2026-11-06).
            st['stage'] = 'approved-ready'
            st.setdefault('resume_from', 'video')
            print(f'ch{ch} eligible for retry from {st["resume_from"]}; storyboard gate applies')
        if (args.refresh or args.resume) and not args.dry_run:
            save_registry(reg)
        active = [ch for ch, st in reg.get('tantrasara', {}).items()
                  if isinstance(st, dict) and st.get('stage') == 'rendering']
        holder = video_lock_holder()
        if active or holder:
            print(f'active or unresolved job: {active}; video lock: {holder} — no new launch')
            return
        for ch, st in reg.get('tantrasara', {}).items():
            if not isinstance(st, dict) or st.get('stage') != 'approved-ready':
                continue
            print(f'NEXT RENDER: ch{ch} (approval and manifest match)')
            if args.run_next and not args.dry_run:
                # Validate even when the registry was not refreshed this run.
                sb = BASE / ('storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json')
                validate_bundle(sb, require_approval=True)
                log = Path(f'/tmp/runall_ch{ch}.log')
                cmd = [sys.executable, str(BASE / 'run_all.py'), '--chapters', ch]
                if st.get('resume_from'):
                    from run_all import STAGES
                    if st['resume_from'] not in STAGES:
                        raise ContractError(f'ch{ch}: invalid resume stage')
                    cmd += ['--from', st['resume_from']]
                with log.open('w', encoding='utf-8') as output:
                    process = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT,
                                               cwd=BASE, start_new_session=True)
                st.update(stage='rendering', log=str(log), pid=process.pid)
                from watch import process_start
                reg.setdefault('processes', {})[f'tantrasara-ch{ch}'] = {
                    'pid': str(process.pid), 'log': str(log),
                    'started': time.strftime('%FT%TZ', time.gmtime()),
                    'proc_start': process_start(process.pid), 'alive': True, 'result': 'running'}
                save_registry(reg)
                print(f'launched pid {process.pid}; check its log and refresh for status')
            return
        print('no approved-ready chapter; review blocked items or the prep queue')


if __name__ == '__main__':
    main()
