#!/usr/bin/env python3
"""Bank emblem gate: emblem samples must be white-background only.

Usage: python3 check_bank.py <samples-dir>
PASS (exit 0) iff every *.png under the dir has a white rim
(mean > 225; RGBA composited on white first). Source photos are exempt
(they get matted); emblems are the law (house VISUALS.md, white law).
"""
import glob as _g
import os as _o
import sys as _s


def rim_mean(path):
    from PIL import Image
    im = Image.open(path)
    if im.mode == 'RGBA':
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        im = bg
    else:
        im = im.convert('RGB')
    w, h = im.size
    rim = []
    for x in range(0, w, 7):
        rim += [im.getpixel((x, 3)), im.getpixel((x, h - 4))]
    for y in range(0, h, 7):
        rim += [im.getpixel((3, y)), im.getpixel((w - 4, y))]
    return sum(sum(p) / 3 for p in rim) / len(rim)


def main():
    if len(_s.argv) < 2:
        print('usage: check_bank.py <samples-dir>')
        return 2
    files = sorted(_g.glob(_o.path.join(_s.argv[1], '*.png')))
    if not files:
        print('BANK FAIL: no emblems found')
        return 1
    bad = 0
    for f in files:
        try:
            m = rim_mean(f)
        except (OSError, ValueError) as e:
            print(f'FAIL ------ {_o.path.basename(f)} ({e})')
            bad += 1
            continue
        ok = m > 225
        bad += not ok
        print(('PASS' if ok else 'FAIL') + f' {m:6.1f} {_o.path.basename(f)}')
    print('BANK ' + ('GREEN' if not bad else f'RED ({bad} non-white)'))
    return 1 if bad else 0


if __name__ == '__main__':
    _s.exit(main())
