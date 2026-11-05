#!/usr/bin/env python3
"""Assemble only current, individually reviewed chunk videos.

Usage: python3 assemble_proven.py STORYBOARD PARTS_DIR OUT.mp4 [MAX_SECS]
`run_blocks.py --finalize` rechecks part hashes, machine gates and every
frame review first. Full-video sidecars record the parts and their reviews.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from factory_contract import (ContractError, clip_inputs, read_json, require_current_review_pack, sha256,
                              require_volume_output, validate_bundle, validate_clip_artifacts,
                              validate_clip_range, validate_schema, video_build_lock)
from proof_contract import require_reviewed_proof

ROOT = Path(__file__).resolve().parent


def duration(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'default=nw=1:nk=1', str(path)],
                            capture_output=True, text=True, check=True)
    value = float(result.stdout.strip())
    if value <= 0:
        raise ContractError(f'{path}: invalid video duration')
    return value


def assemble(storyboard, parts_dir, output, max_secs='600'):
    storyboard, parts_dir, output = Path(storyboard).resolve(), Path(parts_dir).resolve(), Path(output).resolve()
    if output.suffix != '.mp4':
        raise ContractError('assembly output must be an .mp4')
    require_volume_output(parts_dir)
    require_volume_output(output)
    bundle = validate_bundle(storyboard, require_approval=True)
    require_current_review_pack(storyboard)
    finalized = subprocess.run([sys.executable, str(ROOT / 'run_blocks.py'), str(storyboard),
                                str(parts_dir), str(max_secs), '--finalize'],
                               capture_output=True, text=True)
    if finalized.returncode:
        raise ContractError('parts are not ready for assembly: ' + (finalized.stdout + finalized.stderr)[-1200:])
    try:
        parts = [Path(path).resolve() for path in json.loads(finalized.stdout.strip().splitlines()[-1])['parts']]
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise ContractError('part planner did not return a valid part list') from exc
    if not parts:
        raise ContractError('no parts to assemble')
    metas = [validate_clip_artifacts(storyboard, part) for part in parts]
    bids = [bid for meta in metas for bid in meta['bids']]
    audio = [item['path'] for meta in metas for item in meta['provenance']['inputs']['audio']]
    validate_clip_range(bundle, bids)
    spoken = [b['id'] for b in bundle['storyboard']['blocks'] if b['id'] != 'b_opener' and b['voice'] != 'none']
    if bids != spoken:
        raise ContractError('parts do not cover every spoken block exactly once in order')

    lengths = [duration(part) for part in parts]
    coverage, cues, drops, subs = {}, [], {}, []
    offset = 0.0
    for part, meta, length in zip(parts, metas, lengths):
        for key, value in meta['coverage'].items():
            coverage[key] = coverage.get(key, 0) + value
        cues.extend({'key': item['key'], 't': round(item['t'] + offset, 2)} for item in meta['cues'])
        for bid, item in meta['drops'].items():
            if bid in drops:
                raise ContractError(f'duplicate drop {bid} in parts')
            drops[bid] = {'pause': item['pause'], 'at': round(item['at'] + offset, 2)}
        for row in read_json(part.with_suffix('.subs.json')):
            subs.append(dict(row, t=round(row['t'] + offset, 2)))
        offset += length
    validate_schema('subtitles', subs, 'assembled subtitles')
    provenance = clip_inputs(storyboard, bids, audio)
    output.parent.mkdir(parents=True, exist_ok=True)
    with video_build_lock(), tempfile.TemporaryDirectory(prefix='assembly_', dir=output.parent) as tmp:
        tmp = Path(tmp)
        staged_video, staged_subs = tmp / 'output.mp4', tmp / 'output.subs.json'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0',
                        '-i', str(parts_dir / 'concat.txt'), '-c', 'copy', str(staged_video)], check=True)
        actual = duration(staged_video)
        if abs(actual - sum(lengths)) > max(0.3, 0.1 * len(parts)):
            raise ContractError(f'assembly duration {actual:.2f}s differs from parts {sum(lengths):.2f}s')
        staged_subs.write_text(json.dumps(subs, ensure_ascii=False), encoding='utf-8')
        provenance['video_sha256'], provenance['subs_sha256'] = sha256(staged_video), sha256(staged_subs)
        total_coverage = sum(coverage.values())
        meta = {'cuts': sum(item['cuts'] for item in metas), 'duration': round(actual, 2),
                'white_pct': round(100 * coverage.get('white', 0) / total_coverage) if total_coverage else 0,
                'coverage': coverage, 'cues': cues, 'bids': bids, 'drops': drops, 'provenance': provenance}
        validate_schema('render-meta', meta, 'assembled metadata')
        receipt = {'version': 1, 'storyboard_sha256': sha256(storyboard),
                   'video_sha256': sha256(staged_video), 'parts': []}
        for i, part in enumerate(parts):
            proof = parts_dir / 'proofs' / f'p{i:02d}'
            require_reviewed_proof(storyboard, part, proof)
            receipt['parts'].append({'video': str(part), 'video_sha256': sha256(part), 'proof_dir': str(proof),
                                     'manifest_sha256': sha256(proof / 'proof_manifest.json'),
                                     'review_sha256': sha256(proof / 'review.json')})
        if clip_inputs(storyboard, bids, audio)['inputs_sha256'] != provenance['inputs_sha256']:
            raise ContractError('assembly inputs changed while concatenating')
        validate_schema('assembly', receipt, 'assembly receipt')
        staged_meta, staged_receipt = tmp / 'output.render_meta.json', tmp / 'output.assembly.json'
        staged_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
        staged_receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        # Any interrupted multi-file move fails the hash checks on the next stage.
        for source, target in ((staged_video, output), (staged_subs, output.with_suffix('.subs.json')),
                               (staged_meta, output.with_suffix('.render_meta.json')),
                               (staged_receipt, output.with_suffix('.assembly.json'))):
            os.replace(source, target)
    print(f'ASSEMBLED {len(parts)} reviewed parts -> {output} ({actual:.2f}s); verification and owner ears remain')


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    assemble(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) == 5 else '600')
