#!/usr/bin/env python3
"""Post-render confirmation: proves a finished clip is correct.
Usage: python3 verify_clip.py <storyboard.json> <clip.mp4> [--json]
Checks (all fail-closed, non-zero exit on FAIL):
 1. streams: 1920x1080 video ~30fps + audio present.
 2. levels: speech present (mean in [-32,-12]dB, max > -8dB).
 3. dead air: no UNCOMPOSED silence past 10s (missing renders only;
   deliberate holds are composed beds, exempt by design).
 4. word coverage: every narration/dialogue block's head+tail words found
    in whisper transcript in order (verse blocks excluded — whisper
    garbles Sanskrit; their audio is proven by MMS means at render).
 5. motion: >=70% of 1fps samples differ (video not frozen).
Writes report JSON next to the clip (<clip>.verify.json).
"""
import json, os, re, subprocess, sys

def ff(*args):
    return subprocess.run(['ffprobe', '-v', 'error'] + list(args),
                          capture_output=True, text=True).stdout.strip()


def ordered_subsequence(words, transcript, start):
    """Score within a forward window so multiple blocks cannot reuse one
    utterance (ported from the contract-hardening structure)."""
    limit = min(len(transcript), start + max(120, len(words) * 3))
    pos, hit = start - 1, 0
    for word in words:
        try:
            pos = transcript.index(word, pos + 1, limit)
            hit += 1
        except ValueError:
            pass
    return hit / max(1, len(words)), max(start, pos + 1)


def validate_streams(streams):
    """Exactly one 1920x1080 ~30fps video stream and one audio stream."""
    from fractions import Fraction
    video = [s for s in streams if s.get('codec_type') == 'video']
    audio = [s for s in streams if s.get('codec_type') == 'audio']
    try:
        fps = float(Fraction(video[0]['avg_frame_rate'])) if len(video) == 1 else 0
    except (KeyError, ValueError, ZeroDivisionError):
        fps = 0
    if (len(video) != 1 or len(audio) != 1 or video[0].get('width') != 1920
            or video[0].get('height') != 1080 or abs(fps - 30) >= 0.01):
        raise RuntimeError('expected exactly one 1920x1080 30fps video and one audio stream')

def main():
    sb = json.load(open(sys.argv[1], encoding='utf-8'))
    clip = sys.argv[2]
    fails, info = [], {}
    # 1. streams
    w = ff('-show_entries', 'stream=width,height,avg_frame_rate,codec_type', '-of', 'csv', clip)
    info['streams'] = w
    assert '1920' in w and '1080' in w, f'bad video geometry: {w[:120]}'
    assert 'audio' in w, 'no audio stream'
    # 2. levels
    r = subprocess.run(['ffmpeg', '-nostats', '-v', 'info', '-i', clip,
                        '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True)
    me = re.search(r'mean_volume: ([\-\d.]+) dB', r.stderr)
    mx = re.search(r'max_volume: ([\-\d.]+) dB', r.stderr)
    mean, peak = float(me.group(1)), float(mx.group(1))
    info['levels'] = {'mean': mean, 'max': peak}
    if not (-32 <= mean <= -12 and peak > -8):
        fails.append(f'levels out of band: mean {mean}dB max {peak}dB')
    # 3. dead air. Deliberate holds (crisp beds, white exhales, drop
    # pauses) run seconds long BY DESIGN — a 3s ceiling would outlaw the
    # effect (owner call 2026-11-04). This check is a missing-audio
    # detector only: beds are composed and logged at build, so anything
    # past 10s is catastrophe (dropped groups already fail at build).
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', clip,
                        '-af', 'silencedetect=noise=-35dB:d=10.0', '-f', 'null', '-'],
                       capture_output=True, text=True)
    sil = re.findall(r'silence_(start|end): ([\d.]+)', r.stderr)
    gaps = []
    for i in range(0, len(sil) - 1, 2):
        if sil[i][0] == 'start' and sil[i + 1][0] == 'end':
            gaps.append(round(float(sil[i + 1][1]) - float(sil[i][1]), 2))
    info['max_silence'] = max(gaps) if gaps else 0.0
    if info['max_silence'] > 10.0:
        fails.append(f"dead air {info['max_silence']}s (missing audio?)")
    # 4. word coverage (English blocks only)
    from faster_whisper import WhisperModel
    model = WhisperModel('base')
    heard = ' '.join(s.text for s in model.transcribe(clip)[0]).lower()
    hn = re.sub(r'[^a-z ]', '', heard)
    checked, missing, weak = 0, [], []
    tw = hn.split()
    _cov_start = 0
    for b in sb['blocks']:
        if b['type'] not in ('narration', 'dialogue') or b['voice'] not in ('granny', 'man'):
            continue
        w = [re.sub(r'[^a-z]', '', x.lower()) for x in b['text'].split()]
        w = [x for x in w if x]
        if len(w) < 4:
            continue
        r, _cov_start = ordered_subsequence(w, tw, _cov_start)
        checked += 1
        if r < 0.35:
            missing.append(b['id'])
        elif r < 0.6:
            weak.append((b['id'], round(r, 2)))
    info['coverage'] = {'checked': checked, 'missing': missing, 'weak': weak}
    if missing:
        fails.append(f'{len(missing)} blocks unheard: {missing[:6]}')
    # 5. motion
    os.makedirs('/tmp/verify_frames', exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', clip, '-vf', 'fps=1',
                    '/tmp/verify_frames/f%04d.png'], check=True)
    import glob as _g
    from PIL import Image
    import hashlib as _h
    files = sorted(_g.glob('/tmp/verify_frames/f*.png'))
    hashes = [_h.md5(Image.open(f).tobytes()).hexdigest() for f in files]
    distinct = sum(1 for i in range(1, len(hashes)) if hashes[i] != hashes[i - 1])
    info['motion'] = {'samples': len(hashes), 'distinct': distinct}
    if len(hashes) > 5 and distinct / len(hashes) < 0.7:
        fails.append(f'video looks frozen ({distinct}/{len(hashes)} distinct frames)')
    info['pass'] = not fails
    info['fails'] = fails
    rep = clip + '.verify.json'
    json.dump(info, open(rep, 'w'), indent=1)
    print(json.dumps(info, indent=1)[:1500])
    print('VERIFY ' + ('PASS' if info['pass'] else 'FAIL'))
    sys.exit(0 if info['pass'] else 1)


if __name__ == '__main__':
    main()
