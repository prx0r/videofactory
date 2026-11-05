#!/usr/bin/env python3
"""Tie a chunk's visual review to its exact video, gate and proof frames.

`template` prepares a deliberately incomplete review; nobody is approved by
the template. A reviewer must inspect each frame and write their observations.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from factory_contract import (ContractError, read_json, require_current_review_pack, sha256, validate_bundle,
                              validate_clip_artifacts, validate_schema)

ROOT = Path(__file__).resolve().parent.parent / 'builders'


def write_template(proof_dir):
    proof_dir = Path(proof_dir)
    manifest_path = proof_dir / 'proof_manifest.json'
    manifest = read_json(manifest_path)
    validate_schema('proof-manifest', manifest, manifest_path)
    review = {'version': 1, 'proof_manifest_sha256': sha256(manifest_path),
              'reviewer': '', 'reviewed_on': '',
              'frames': [{'file': frame['file'], 'sha256': frame['sha256'],
                          'verdict': 'unreviewed', 'observation': ''}
                         for frame in manifest['frames']]}
    target = proof_dir / 'review.template.json'
    target.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target


def require_reviewed_proof(storyboard, video, proof_dir):
    """Require current machine evidence and an explicit per-frame review."""
    proof_dir, video = Path(proof_dir), Path(video)
    bundle = validate_bundle(storyboard, require_approval=True)
    validate_clip_artifacts(storyboard, video)
    mp = proof_dir / 'proof_manifest.json'
    rp = proof_dir / 'review.json'
    manifest, review = read_json(mp), read_json(rp)
    validate_schema('proof-manifest', manifest, mp)
    validate_schema('proof-review', review, rp)
    paths = bundle['paths']
    expected = {
        'storyboard_sha256': sha256(paths['storyboard']),
        'glossary_sha256': sha256(paths['glossary']),
        'approval_sha256': sha256(paths['approval']),
        'video_sha256': sha256(video),
        'meta_sha256': sha256(video.with_suffix('.render_meta.json')),
        'subs_sha256': sha256(video.with_suffix('.subs.json')),
        'gate_sha256': sha256(proof_dir / 'gate.txt'),
    }
    if manifest['lane'] != paths['lane'] or manifest['unit'] != paths['unit']:
        raise ContractError(f'{mp}: proof is for a different unit')
    if not manifest['machine_passed'] or any(manifest.get(k) != v for k, v in expected.items()):
        raise ContractError(f'{mp}: machine proof is red or its artifacts changed')
    if review['proof_manifest_sha256'] != sha256(mp):
        raise ContractError(f'{rp}: review is for a different proof manifest')
    frames = {entry['file']: entry for entry in manifest['frames']}
    reviewed = {entry['file']: entry for entry in review['frames']}
    if len(frames) != len(manifest['frames']) or len(reviewed) != len(review['frames']) or set(frames) != set(reviewed):
        raise ContractError(f'{rp}: review must cover every proof frame exactly once')
    for name, frame in frames.items():
        record = reviewed[name]
        if (sha256(proof_dir / name) != frame['sha256'] or
                record['sha256'] != frame['sha256'] or record['verdict'] != 'pass'):
            raise ContractError(f'{rp}: {name} is changed, unreviewed or failed')
    cmd = [sys.executable, str(ROOT / 'gate_visual.py'), str(paths['storyboard']),
           '--glossary', str(paths['glossary']), '--approved', str(paths['approval']),
           '--meta', str(video.with_suffix('.render_meta.json')),
           '--subs', str(video.with_suffix('.subs.json')), '--mp4', str(video)]
    gate = subprocess.run(cmd, capture_output=True, text=True)
    if gate.returncode:
        raise ContractError(f'{proof_dir}: current visual machine gate failed: '
                            + (gate.stdout + gate.stderr)[-600:])
    return review


def require_reviewed_assembly(storyboard, video):
    """Recheck the full video's part order and every current proof review."""
    video = Path(video)
    require_current_review_pack(storyboard)
    meta = validate_clip_artifacts(storyboard, video)
    receipt_path = video.with_suffix('.assembly.json')
    receipt = read_json(receipt_path)
    validate_schema('assembly', receipt, receipt_path)
    if receipt['video_sha256'] != sha256(video) or receipt['storyboard_sha256'] != sha256(storyboard):
        raise ContractError(f'{receipt_path}: assembly is for different bytes')
    bids, audio, seen = [], [], set()
    for part in receipt['parts']:
        part_video, proof_dir = Path(part['video']), Path(part['proof_dir'])
        if str(part_video) in seen:
            raise ContractError(f'{receipt_path}: duplicate part')
        seen.add(str(part_video))
        if (part['video_sha256'] != sha256(part_video) or
                part['manifest_sha256'] != sha256(proof_dir / 'proof_manifest.json') or
                part['review_sha256'] != sha256(proof_dir / 'review.json')):
            raise ContractError(f'{receipt_path}: part or review changed')
        require_reviewed_proof(storyboard, part_video, proof_dir)
        part_meta = validate_clip_artifacts(storyboard, part_video)
        bids.extend(part_meta['bids'])
        audio.extend(entry['path'] for entry in part_meta['provenance']['inputs']['audio'])
    if bids != meta['bids'] or audio != [entry['path'] for entry in meta['provenance']['inputs']['audio']]:
        raise ContractError(f'{receipt_path}: assembled part order differs from the video metadata')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    template = sub.add_parser('template')
    template.add_argument('proof_dir')
    check = sub.add_parser('check')
    check.add_argument('storyboard')
    check.add_argument('video')
    check.add_argument('proof_dir')
    args = parser.parse_args()
    if args.action == 'template':
        print(f'Wrote {write_template(args.proof_dir)} — complete it as review.json after inspecting frames.')
    else:
        review = require_reviewed_proof(args.storyboard, args.video, args.proof_dir)
        print(f"PROOF PASS — {review['reviewer']} reviewed {len(review['frames'])} frames")


if __name__ == '__main__':
    main()
