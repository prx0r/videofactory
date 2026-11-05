#!/usr/bin/env python3
"""Publish the pre-render review pack: full storyboard (readable) + holds
timeline + contact sheets, uploaded to R2 for owner sign-off.
Usage: python3 publish_review.py <ch>
Writes review/ch<NN>/ {storyboard.md, timeline.md, manifest.json} locally
(sheets stay on volume/R2, never committed) and uploads to
r2:svread-audio/tantrasara/review/ch<NN>/.
Owner confirms by message; engineer records approved_ch<NN>.json (that file
is the render gate — see run_all.stage_render).
"""
import json, os, subprocess, sys, hashlib, datetime, tempfile, atexit, shutil
from pathlib import Path

import sys as _sys2
_sys2.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
TOOLS = os.path.dirname(os.path.abspath(__file__))
# DATA travels with the series repo (drivers export VF_REPO from
# series/*.json); default is the script dir so copied-publisher fixtures
# and single-repo checkouts keep working (codex behavior).
DATA = _vf.repo_root() if 'VF_REPO' in os.environ else TOOLS
BASE = DATA
def main():
    ch = sys.argv[1].zfill(2)
    SB = f'{DATA}/storyboard_ch6.json' if ch == '06' else f'{DATA}/storyboard_ch{ch}.json'
    GL = f'{DATA}/glossary_ch{ch}.json'
    OUT = f'{DATA}/review/ch{ch}'
    os.makedirs(OUT, exist_ok=True)

    from factory_contract import read_json, sha256 as contract_sha256, validate_bundle
    bundle = validate_bundle(SB)
    sb, gl = bundle['storyboard'], bundle['glossary']
    snapshot = {p: contract_sha256(p) for p in (SB, GL, __file__, f'{TOOLS}/holds_timeline.py')}
    if read_json(SB) != sb or read_json(GL) != gl:
        raise RuntimeError('review inputs changed while they were loaded')
    def check_snapshot():
        if any(contract_sha256(p) != digest for p, digest in snapshot.items()):
            raise RuntimeError('review inputs or builders changed during publication')
    marker = Path(OUT) / '.publish-in-progress'
    marker.write_text('Remove only after all review uploads and the manifest succeed.\n', encoding='utf-8')
    confirmed = sorted(k for k, v in gl.items() if v.get('status') == 'confirmed')

    errs = sb.get('validation', {}).get('errors', [])
    assert not errs, f'ch{ch}: storyboard not green — publish refused'

    # 1. readable storyboard: every block, voice, first 220 chars
    lines = [f'# Review — chapter {ch}', '',
             f'{len(sb["blocks"])} blocks. Voices: ' +
             ', '.join(f'{v}={sum(1 for b in sb["blocks"] if b["voice"]==v)}'
                       for v in sorted(set(b['voice'] for b in sb['blocks']))) + '.',
             f'Confirmed glossary terms ({len(confirmed)}): ' + (', '.join(confirmed) or 'none') + '.', '']
    for b in sb['blocks']:
        t = b['text'].replace('\n', ' / ')
        lines += [f"## {b['id']} · {b['type']} · {b['voice']} · [{b.get('section','')[:40]}]", '',
                  t, '']
    Path(OUT, 'storyboard.md').write_text('\n'.join(lines), encoding='utf-8')

    # 2. holds timeline (planning estimate, 150wpm — real timings at render)
    r = subprocess.run(['python3', f'{TOOLS}/holds_timeline.py', SB, GL, f'{OUT}/timeline.md'],
                       capture_output=True, text=True, check=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'timeline: no terms')

    # 3. contact sheets (cards only, no audio)
    sheet_dir = tempfile.mkdtemp(prefix=f'tantra_review_ch{ch}_', dir='/tmp')
    atexit.register(shutil.rmtree, sheet_dir, ignore_errors=True)
    r = subprocess.run(['python3', f'{TOOLS}/render_holds.py', SB, sheet_dir],
                       capture_output=True, text=True, check=True)
    if not os.path.isfile(f'{sheet_dir}/contact_sheet.png'):
        raise RuntimeError('contact sheet was not produced')
    print('sheets:', (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else 'ok'))

    def sha(p):
        with open(p, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    check_snapshot()
    manifest = {'chapter': ch, 'date': datetime.date.today().isoformat(),
                'blocks': len(sb['blocks']),
                'storyboard_sha': snapshot[SB], 'glossary_sha': snapshot[GL],
                'confirmed_terms': confirmed, 'storyboard_view_sha': sha(f'{OUT}/storyboard.md'),
                'timeline_sha': sha(f'{OUT}/timeline.md'), 'sheet_sha': sha(f'{sheet_dir}/contact_sheet.png'),
                'publisher_sha': snapshot[__file__], 'timeline_builder_sha': snapshot[f'{TOOLS}/holds_timeline.py'],
                'approved': False}
    from factory_contract import validate_schema
    validate_schema('review-manifest', manifest, 'new review manifest')

    # 4. upload (storyboard + timeline + sheets)
    subprocess.run(['rclone', 'copyto', f'{OUT}/storyboard.md',
                    f'{_vf.r2_prefix()}/review/ch{ch}/storyboard.md'], check=True)
    subprocess.run(['rclone', 'copyto', f'{OUT}/timeline.md',
                    f'{_vf.r2_prefix()}/review/ch{ch}/timeline.md'], check=True)
    subprocess.run(['rclone', 'copy', sheet_dir,
                    f'{_vf.r2_prefix()}/review/ch{ch}/sheets'], check=True)
    check_snapshot()
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=OUT, delete=False) as f:
        json.dump(manifest, f, indent=1)
        temp_manifest = f.name
    os.replace(temp_manifest, f'{OUT}/manifest.json')
    marker.unlink()
    print(f'published: review/ch{ch}/ (manifest approved=false — awaiting owner)')
    print(f'https://pub-87169194562a44fcb8279a799d626c62.r2.dev/tantrasara/review/ch{ch}/storyboard.md')



if __name__ == '__main__':
    main()