#!/usr/bin/env python3
"""check_avsync.py — A/V duration sync check (advisory/record-only, never gates).

Usage: python3 check_avsync.py <clip.mp4> [--spotify] [--json]

Probes video vs audio stream durations with ffprobe (read-only; no encode,
safe on any host). AAC padding normally leaves audio ~20-35ms longer than
video — expected, not a defect. Strict distributors (Spotify) reject any
delta > 0, so Spotify-target outputs need a trimmed remux.

Thresholds:
  standard: PASS if abs(audio - video) <= 0.080s, WARN to 0.150s, else FAIL
  spotify:  PASS only if abs(audio - video) <= 0.010s, else FAIL

Fix (run on the render box, never the hub per Rule 8):
  VDUR=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration \
    -of default=nw=1:nk=1 <clip>)
  ffmpeg -y -v error -i <clip> -c copy -t "$VDUR" <clip-spotify.mp4>
then re-run this checker with --spotify to confirm <=10ms.

Exit 0 on PASS, 1 on FAIL/WARN-missing-evidence. Prints human line plus
optional JSON with --json. Record-only: the render gate stays storyboard
green + owner approval (owner order 2026-11-06).
"""
import json
import subprocess
import sys

STD_TOL_S = 0.080
WARN_TOL_S = 0.150
SPOTIFY_TOL_S = 0.010


def probe_durations(clip):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries',
         'stream=index,codec_type,codec_name,duration',
         '-of', 'json', clip],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffprobe failed: %s' % (r.stderr.strip()[:200]))
    doc = json.loads(r.stdout or '{}')
    vdur, adur, vcodec, acodec = None, None, None, None
    for s in doc.get('streams', []):
        try:
            d = float(s.get('duration')) if s.get('duration') not in (None, 'N/A') else None
        except (TypeError, ValueError):
            d = None
        if s.get('codec_type') == 'video' and vdur is None:
            vdur, vcodec = d, s.get('codec_name')
        elif s.get('codec_type') == 'audio' and adur is None:
            adur, acodec = d, s.get('codec_name')
    return vdur, adur, vcodec, acodec


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    spotify = '--spotify' in sys.argv
    want_json = '--json' in sys.argv
    if not args:
        print('usage: check_avsync.py <clip.mp4> [--spotify] [--json]')
        return 2
    clip = args[0]
    try:
        vdur, adur, vcodec, acodec = probe_durations(clip)
    except Exception as e:
        print('AVSYNC FAIL %s: %s' % (clip, e))
        return 1
    if vdur is None or adur is None:
        print('AVSYNC FAIL %s: missing stream durations (video=%s audio=%s)' % (clip, vdur, adur))
        return 1
    delta = adur - vdur
    tol = SPOTIFY_TOL_S if spotify else STD_TOL_S
    mode = 'spotify-strict' if spotify else 'standard'
    verdict = 'PASS' if abs(delta) <= tol else ('WARN' if (not spotify and abs(delta) <= WARN_TOL_S) else 'FAIL')
    info = {'clip': clip, 'mode': mode, 'video_codec': vcodec, 'audio_codec': acodec,
            'video_duration': round(vdur, 3), 'audio_duration': round(adur, 3),
            'delta_ms': round(delta * 1000, 1), 'tolerance_ms': round(tol * 1000, 1),
            'verdict': verdict, 'note': 'AAC padding ~20-35ms audio-long is normal; strict targets trim to video'}
    if want_json:
        print(json.dumps(info, indent=1))
    print('AVSYNC %s %s delta=%+.1fms tol=%.0fms (%s/%s)' % (
        verdict, clip, info['delta_ms'], info['tolerance_ms'], vcodec, acodec))
    if verdict == 'FAIL':
        print('fix (render box only): ffmpeg -i <clip> -c copy -t %.3f <clip-spotify.mp4' % vdur)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
