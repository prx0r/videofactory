#!/usr/bin/env python3
"""Full hold-card set in locked house style + contact sheet.
Usage: python3 render_holds.py <storyboard.json> <outdir>
Single source of truth for cards: holds.py (shared with build_clip.py).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import holds as H
from PIL import Image, ImageDraw


def main():
    sb = json.load(open(sys.argv[1], encoding='utf-8'))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    # chapter glossary for term layers (review mode: proposed shown as-is,
    # video gates on confirmed). Lane-aware: shiva storyboards resolve the
    # shiva lane (own glossaries, own thumbnail dir).
    lane = H.lane_for(sys.argv[1])
    _ch = lane['ch']
    gl = json.load(open(lane['glossary'], encoding='utf-8')) if os.path.exists(lane['glossary']) else {}
    groups = H.build_holds(sb['blocks'])
    flat = sb['blocks']
    idx = {b['id']: i for i, b in enumerate(flat)}
    files = []
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import lane_api as _api
    _sb_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else ''
    _intro = _api.intro_args(_sb_arg or 'tantrasara/storyboard_ch01.json', sb['blocks'], gl)
    _title = _intro['title']
    for hi, h in enumerate(groups):
        last_id = h[-1]['id']
        if h[0].get('id') == 'b_opener':
            # sheets show the same intro bug the video burns
            _ih = H.intro_hold(_ch, _title, lane['assets'], lane['thumbbox'], _intro['numeral'], lane['art_center'], _intro['header'])
            im = _ih if _ih is not None else H.render_hold(h, None, gl)
            fn = f'{out}/hold{hi:03d}.png'
            im.save(fn)
            files.append(fn)
            continue
        sub = ''
        for b in flat[idx[last_id] + 1:idx[last_id] + 6]:
            if b.get('type') in ('narration', 'dialogue') and b.get('voice') in ('granny', 'man'):
                # sheets share the subtitle face: Deva words go IAST (M3)
                import re as _re
                sub = ' '.join(H.to_iast(w) if _re.search(r'[\u0900-\u097F]', w) else w
                               for w in b['text'][:140].split())
                break
        im = H.render_hold(h, sub if sub else None, gl)
        fn = f'{out}/hold{hi:03d}.png'
        im.save(fn)
        files.append(fn)
    print(f'rendered {len(files)} holds')
    cols, cw, chh = 4, 480, 270
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new('RGB', (cw * cols, rows * chh + 40), (245, 243, 238))
    sd = ImageDraw.Draw(sheet)
    sd.text((16, 8), f'{lane["lane"].capitalize()} holds — {len(files)} cards', fill=H.INK,
            font=H.F(H.FE, 22))
    for i, f in enumerate(files):
        sheet.paste(Image.open(f).resize((cw, chh)), ((i % cols) * cw, 40 + (i // cols) * chh))
    sheet.save(f'{out}/contact_sheet.png')
    print('sheet:', f'{out}/contact_sheet.png')


if __name__ == '__main__':
    main()
