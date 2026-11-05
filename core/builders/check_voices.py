#!/usr/bin/env python3
"""Sample audio energy at each planned seat's onsets in this exact video.

Usage: python3 check_voices.py <storyboard.json> <full.mp4>
This detects wholly silent sampled seats; energy is NOT speaker identity or
pronunciation recognition. A different voice or overlapping sound can still
be audible. Owner listening and review remain required.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from factory_contract import (read_json, sha256, validate_bundle, validate_clip_artifacts,
                              validate_schema)


def vol(mp4, t0, dur):
    result = subprocess.run(
        ['ffmpeg', '-nostats', '-v', 'info', '-ss', str(max(0.0, t0)), '-i', mp4,
         '-t', str(dur), '-af', 'volumedetect', '-f', 'null', '-'],
        capture_output=True, text=True)
    match = re.search(r'mean_volume: ([\-\d.]+) dB', result.stderr)
    return float(match.group(1)) if result.returncode == 0 and match else -91.0


def main():
    sb_path, mp4 = sys.argv[1], sys.argv[2]
    report_path = str(Path(mp4).with_suffix('.voices.json'))
    Path(report_path).unlink(missing_ok=True)
    bundle = validate_bundle(sb_path, require_approval=True)
    validate_clip_artifacts(sb_path, mp4)
    subs_path = Path(mp4).with_suffix('.subs.json')
    subs = read_json(subs_path)
    validate_schema('subtitles', subs, subs_path)
    bybid = {}
    for row in subs:
        bybid.setdefault(row['bid'], []).append(row)
    starts = {bid: min(row['t'] for row in rows) for bid, rows in bybid.items()}
    byvoice = {}
    for block in bundle['storyboard']['blocks']:
        if block['voice'] in ('granny', 'man', 'verse'):
            byvoice.setdefault(block['voice'], []).append(block['id'])
    checks = []
    for voice, bids in sorted(byvoice.items()):
        have = [bid for bid in bids if bid in bybid]
        picks = have[::max(1, len(have) // 5)][:5]
        levels = []
        for bid in picks:
            rows = sorted(bybid[bid], key=lambda row: row['t'])
            onset = rows[0]['t']
            later = [t for other, t in starts.items() if other != bid and t > onset]
            end = min(rows[-1]['t'] + 0.2, min(later) if later else float('inf'))
            begin = onset + 0.02
            db = vol(mp4, begin, min(10.0, end - begin)) if end > begin else -91.0
            levels.append({'bid': bid, 't': round(onset, 2), 'mean_db': round(db, 1)})
        audible = [item for item in levels if item['mean_db'] > -40.0]
        checks.append({'voice': voice, 'samples': levels, 'audible': len(audible), 'pass': bool(audible)})
        print(f"{'PASS' if audible else 'FAIL'} {voice}: {len(audible)}/{len(levels)} audible samples")
    report = {'version': 1, 'storyboard_sha256': sha256(sb_path), 'video_sha256': sha256(mp4),
              'subs_sha256': sha256(subs_path), 'checker_sha256': sha256(__file__), 'checks': checks,
              'pass': bool(checks) and all(item['pass'] for item in checks),
              'limitation': 'Energy at expected onsets does not identify the speaker.'}
    temporary = report_path + f'.tmp-{os.getpid()}'
    Path(temporary).write_text(json.dumps(report, indent=2), encoding='utf-8')
    os.replace(temporary, report_path)
    print('VOICE ENERGY ' + ('PRESENT' if report['pass'] else 'MISSING'))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
