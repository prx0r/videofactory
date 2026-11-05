#!/usr/bin/env python3
"""Release packager: verified chapter mp4s -> combined film + zip.
Usage: python3 release.py [--chapters 01,02] [--dry-run] [--gap 5.0]
Combines full-chapter mp4s (/tmp/chNN_full.mp4) with GAP seconds of clean
white + silence between chapters, then zips mp4s + manifest + coverage
report. Refuses anything unverified: every chapter needs verify PASS
(<clip>.verify.json) beside its mp4, or it is skipped loudly (never
silently dropped).
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
import json, os, subprocess, sys, zipfile, datetime

BASE = _vf.repo_root()
GAP = 5.0
W, H = 1920, 1080


def main():
    args = sys.argv[1:]
    chs = (args[args.index('--chapters') + 1].split(',') if '--chapters' in args
           else [f'{i:02d}' for i in range(1, 23)])
    dry = '--dry-run' in args
    gap = float(args[args.index('--gap') + 1]) if '--gap' in args else GAP
    ready, skipped = [], []
    for ch in chs:
        mp4 = f'/tmp/ch{ch}_full.mp4'
        ver = mp4 + '.verify.json'
        ok = os.path.exists(mp4) and os.path.exists(ver) and json.load(open(ver)).get('pass')
        (ready if ok else skipped).append(ch)
    print(f'ready: {ready}')
    print(f'skipped (no verified mp4): {skipped}')
    if not ready:
        print('nothing to release')
        return
    date = datetime.date.today().isoformat()
    outdir = f'/tmp/release_{date}'
    os.makedirs(outdir, exist_ok=True)
    if dry:
        print(f'DRY RUN — would combine {len(ready)} chapters with {gap}s blanks + zip')
        return
    # 5s (or --gap) clean white + silence between chapters. Inputs lay out
    # as ch0, blankV, blankA, ch1, blankV, blankA, ... (mono throughout,
    # matching every bed the pipeline ever made).
    n = len(ready)
    segs = []
    for i, ch in enumerate(ready):
        segs += ['-i', f'/tmp/ch{ch}_full.mp4']
        if i < len(ready) - 1:
            segs += ['-f', 'lavfi', '-i', f'color=white:s={W}x{H}:r=30:d={gap}',
                     '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=mono:d={gap}']
    parts = []
    for i in range(n):
        parts.append(f'[{3*i}:v][{3*i}:a]')
        if i < n - 1:
            parts.append(f'[{3*i+1}:v][{3*i+2}:a]')
    filt = ''.join(parts) + f'concat=n={2*n-1}:v=1:a=1'
    combined = f'{outdir}/tantrasara_full.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error'] + segs +
                   ['-filter_complex', filt, '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '18', '-c:a', 'aac', '-b:a', '192k', combined], check=True)
    manifest = {'date': date, 'chapters': ready, 'skipped': skipped, 'gap': gap,
                'combined': os.path.basename(combined)}
    json.dump(manifest, open(f'{outdir}/manifest.json', 'w'), indent=1)
    zp = f'{outdir}/tantrasara_release_{date}.zip'
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(combined, os.path.basename(combined))
        z.write(f'{outdir}/manifest.json', 'manifest.json')
        for ch in ready:
            z.write(f'/tmp/ch{ch}_full.mp4', f'ch{ch}_full.mp4')
    print(f'OK: {combined} + {zp}')


if __name__ == '__main__':
    main()
