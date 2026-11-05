#!/usr/bin/env python3
"""Proof pack for one chunk part (the autonomous visual loop).
Usage: python3 prove_clip.py <storyboard.json> <part.mp4> <outdir>
Reads <part>.render_meta.json + .subs.json (written by build_clip):
boundary frames at thumbnail, every cue onset, every drop hold,
plus two mid-speech frames; contact sheet + index with the expected
card per the storyboard; gate_visual machine run; notes template.
Eye (human or Qwen) reads the pack against the storyboard beats —
that read is the gate. Nothing downstream runs on red.
"""
import json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
TOOLS = os.path.dirname(os.path.abspath(__file__))
BASE = TOOLS


def frame(mp4, t, out):
    Path(out).unlink(missing_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(max(0.0, t)),
                    '-i', mp4, '-frames:v', '1', out], check=True)
    if not os.path.exists(out) or not os.path.getsize(out):
        raise RuntimeError(f'ffmpeg produced no frame at {t}s')


def main():
    sb_path, mp4, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    from factory_contract import sha256, validate_bundle, validate_clip_artifacts
    bundle = validate_bundle(sb_path, require_approval=True)
    validate_clip_artifacts(sb_path, mp4)
    Path(outdir, 'proof_manifest.json').unlink(missing_ok=True)
    Path(outdir, 'review.template.json').unlink(missing_ok=True)
    sb = json.load(open(sb_path, encoding='utf-8'))
    meta = json.load(open(os.path.splitext(mp4)[0] + '.render_meta.json', encoding='utf-8'))
    subs = json.load(open(os.path.splitext(mp4)[0] + '.subs.json', encoding='utf-8'))
    byid = {b['id']: b for b in sb['blocks']}
    dur = meta['duration']
    starts_top = meta['bids'][0] == 'b1'
    shots = [('t0-opening', 0.5, 'thumbnail opens' if starts_top else 'mid-chapter opening')]
    for i, c in enumerate(meta.get('cues', [])):
        shots.append((f"cue-{i:04d}-{c['key']}", max(0.0, c['t'] + 0.15), f"card {c['key']} just on"))
    first_onsets = {}
    for row in subs:
        first_onsets.setdefault(row['bid'], row['t'])
    previous_section = None
    for bid in meta['bids']:
        block = byid[bid]
        section_change = previous_section is not None and block['section'] != previous_section
        previous_section = block['section']
        if bid not in first_onsets:
            continue
        if (block['type'] in ('verse', 'dialogue') or section_change
                or block.get('directed', '').startswith('[long pause]')):
            shots.append((f'boundary-{bid}', max(0.0, first_onsets[bid] + 0.15),
                          f"{block['type']} or tone boundary at {bid}"))
    for bid, d in meta.get('drops', {}).items():
        shots.append((f"drop-{bid}", d['at'] + (d.get('pause', 1.0) / 2),
                      f"white hold across {d.get('pause')}s pause"))
    for frac, name in ((0.33, 'mid-speech-1'), (0.66, 'mid-speech-2')):
        shots.append((name, dur * frac, 'karaoke on the spoken word'))
    idx = []
    for name, t, expect in shots:
        fp = os.path.join(outdir, f'{name}.png')
        try:
            frame(mp4, t, fp)
            idx.append((name, round(t, 1), expect, 'ok'))
        except (subprocess.CalledProcessError, RuntimeError) as e:
            idx.append((name, round(t, 1), expect, f'FRAME FAIL {e}'))
    with open(os.path.join(outdir, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(f'# Proof {os.path.basename(mp4)} — {meta["cuts"]} cuts, '
                f'{dur}s, white {meta["white_pct"]}%\n\n')
        for name, t, expect, st in idx:
            f.write(f'- [{st}] {name}.png @ {t}s — expect: {expect}\n')
        f.write('\n## Eye notes (fill per frame: right card / subtitle / karaoke / tofu / overflow)\n')
    # contact sheet
    from PIL import Image
    files = [os.path.join(outdir, n + '.png') for n, _, _, st in idx if st == 'ok']
    if files:
        cols, cw, chh = 3, 640, 360
        rows = (len(files) + cols - 1) // cols
        sheet = Image.new('RGB', (cw * cols, rows * chh + 40), (245, 243, 238))
        for i, fp in enumerate(files):
            sheet.paste(Image.open(fp).resize((cw, chh)), ((i % cols) * cw, 40 + (i // cols) * chh))
        sheet.save(os.path.join(outdir, 'contact_sheet.png'))
    # machine gate (presence of meta/subs/mp4 asserted inside)
    paths = bundle['paths']
    cmd = ['python3', f'{BASE}/gate_visual.py', sb_path, '--meta',
           os.path.splitext(mp4)[0] + '.render_meta.json', '--subs',
           os.path.splitext(mp4)[0] + '.subs.json', '--mp4', mp4,
           '--glossary', str(paths['glossary']), '--approved', str(paths['approval'])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    open(os.path.join(outdir, 'gate.txt'), 'w').write(r.stdout + r.stderr)
    print(open(os.path.join(outdir, 'gate.txt')).read())
    print(f'proof: {outdir} ({len(files)} frames + gate + index)')
    if r.returncode or any(status != 'ok' for _, _, _, status in idx):
        print('PROOF RED: machine gate or frame extraction failed; no review manifest written')
        return 1
    manifest = {
        'version': 1, 'lane': paths['lane'], 'unit': paths['unit'],
        'storyboard_sha256': sha256(paths['storyboard']),
        'glossary_sha256': sha256(paths['glossary']),
        'approval_sha256': sha256(paths['approval']),
        'video_sha256': sha256(mp4),
        'meta_sha256': sha256(os.path.splitext(mp4)[0] + '.render_meta.json'),
        'subs_sha256': sha256(os.path.splitext(mp4)[0] + '.subs.json'),
        'gate_sha256': sha256(os.path.join(outdir, 'gate.txt')),
        'machine_passed': True,
        'frames': [{'file': name + '.png', 'at': t, 'expected': expected,
                    'sha256': sha256(os.path.join(outdir, name + '.png'))}
                   for name, t, expected, _ in idx],
    }
    with open(os.path.join(outdir, 'proof_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    from proof_contract import write_template
    print(f'Inspect every frame, then complete {write_template(outdir)} as review.json.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
