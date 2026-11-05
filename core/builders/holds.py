#!/usr/bin/env python3
"""Shared hold-card logic: storyboard blocks -> holds -> rendered cards.
One implementation used by render_holds.py (contact sheets) and build_clip.py
(video). Verse cards are Devanagari ONLY (no romanisation, owner call).
Narration with no anchor hold shows a clean blank card.
"""
import os as _os, re, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
LIGHT, INK, FADE = (255, 255, 255), (23, 20, 15), (207, 201, 190)
ROMAN_FILL = (221, 215, 203)   # IAST — lightest, closest to the Sanskrit
LIT_FILL = (188, 180, 165)     # intermediary literal — a step closer
FINAL_FILL = (105, 99, 86)     # final English — closest our English gets
FD = _vf.fonts()['deva']
FR = _vf.fonts()['gloss']
FE = _vf.fonts()['subtitle']
SUB_Y = 860
SAFE_MARGIN = 85  # card ink stays 85px+ inside frame edges, above SUB_Y
CANVAS_W, CANVAS_H = 1280, 660  # mini canvas for overlay clips, centered safe
CANVAS_X = (W - CANVAS_W) // 2
CANVAS_Y = 90 + (SUB_Y - 90 - CANVAS_H) // 2

_HOLD_RENDERERS = {}  # kind -> fn(d, im, hold, sub_text, glossary)


def assert_safe(y_bottom, detail=''):
    """Custom cards call this: card ink must clear the subtitle zone."""
    assert y_bottom <= SUB_Y, f'card collides with subtitle zone {detail} — split the stack'


def register_hold(kind, fn):
    """Extension point for new on-screen things (future layers, series
    devices): register a card renderer instead of editing core dispatch.
    fn(d, im, hold, sub_text, glossary) draws the card; the shared
    subtitle footer still applies; call assert_safe on your lowest ink.
    Core kinds (opener/title/figure/verse) are not overridable. Computation
    (when the card appears) lives in build_holds / the video cue resolver —
    register rendering here, add the cue rule there, gate both."""
    if kind in ('opener', 'title', 'figure', 'verse'):
        raise ValueError(f'core kind {kind} is not overridable — register a new kind')
    _HOLD_RENDERERS[kind] = fn
MAX_PAIRS = 3


def F(p, size):
    return ImageFont.truetype(p, size)


def ct(d, y, s, font, fill=INK):
    d.text(((W - d.textlength(s, font=font)) / 2, y), s, font=font, fill=fill)


def chapter_title(blocks, glossary=None):
    """Canonical title source: first block carrying Devanagari (the
    chapter-name line, b2 in every chapter — any voice, since b2 chants).
    Display Deva is the prakāśana name (roman half transliterated) so every
    chapter titles by name, not by ordinal. Lookup key follows the display
    Deva. Layers from the glossary entry when present — Deva+IAST minimum,
    always."""
    import unicodedata
    for b in blocks:
        if b.get('id') == 'b_opener':
            continue
        if b.get('voice') == 'none':
            continue
        deva_part, roman_part = split_scripts(b['text'])
        if not deva_part:
            continue
        try:
            name_deva = to_deva(roman_part) if roman_part else deva_part
        except Exception:
            name_deva = deva_part
        v = (glossary or {}).get(verse_match_key(name_deva), '')
        literal = final = ''
        if isinstance(v, dict):
            literal, final = v.get('literal', ''), v.get('gloss', '')
            if isinstance(final, dict):
                final = final.get('gloss', '')
        try:
            iast = to_iast(name_deva)
        except Exception:
            iast = roman_part
        return {'deva': name_deva, 'iast': iast, 'literal': literal,
                'final': final if isinstance(final, str) else ''}
    return None


PHONEME_DIR = _vf.phoneme_dir()
VOICE_DB = -21.0      # house voice norm, all seats incl. human clips
# Human phoneme clips (owner call 2026-11-04): sounded single phonemes
# use these exact human recordings, never Fish/granny. Verses stay Fish.
# Only certain 1:1 mappings listed — ambiguous clips (retroflex
# da1/tha1/na1, na_j/na_k, sha/shha, lr/lrr) fall back to Fish.
PHONEMES = {
    'a': 'a.ogg', 'ā': 'aa.ogg', 'i': 'i.ogg', 'ī': 'ii.ogg',
    'u': 'u.ogg', 'ū': 'uu.ogg', 'ṛ': 'r.ogg', 'ṝ': 'rr.ogg',
    'e': 'e.ogg', 'ai': 'ai.ogg', 'o': 'o.ogg', 'au': 'au.ogg',
    'ṃ': 'anusvara.ogg', 'ḥ': 'visarga.ogg',
    'ka': 'ka.ogg', 'kha': 'kha.ogg', 'ga': 'ga.ogg', 'gha': 'gha.ogg',
    'ca': 'ca.ogg', 'cha': 'cha.ogg', 'ja': 'ja.ogg', 'jha': 'jha.ogg',
    'ta': 'ta.ogg', 'tha': 'tha.ogg', 'da': 'da.ogg', 'dha': 'dha.ogg',
    'na': 'na.ogg', 'pa': 'pa.ogg', 'pha': 'pha.ogg', 'ba': 'ba.ogg',
    'bha': 'bha.ogg', 'ma': 'ma.ogg', 'ya': 'ya.ogg', 'ra': 'ra.ogg',
    'la': 'la.ogg', 'va': 'va.ogg', 'sa': 'sa.ogg', 'ha': 'ha.ogg',
}


def human_phoneme_key(block):
    """IAST key if this block is one sounded phoneme, else None."""
    from indic_transliteration.sanscript import transliterate, DEVANAGARI, IAST
    toks = [w.strip('—.,!?;:—-') for w in block['text'].strip().split()]
    toks = [t for t in toks if t]
    if not toks:
        return None
    try:
        conv = [transliterate(t, DEVANAGARI, IAST) if re.search(r'[\u0900-\u097F]', t) else t
                for t in toks]
    except Exception:
        return None
    if len(set(conv)) == 1 and conv[0] in PHONEMES:
        return conv[0]
    return None


def is_phoneme_block(block):
    """A verse block sounding one mapped phoneme: always its own group
    (owner call 2026-11-04), so the human clip carries it alone."""
    return (block.get('voice') == 'verse' and block.get('type') == 'verse'
            and human_phoneme_key(block) is not None)


def split_phoneme_groups(groups):
    """Carve lone-phoneme verse blocks out of merged groups. Same
    everywhere (render, assemble, video, gates) — one rule."""
    out = []
    for g in groups:
        if g and g[0].get('group_kind') == 'opener':
            out.append(g)
            continue
        cur = []
        for b in g:
            if is_phoneme_block(b):
                if cur:
                    out.append(cur)
                    cur = []
                out.append([b])
            else:
                if cur and (cur[0]['section'], cur[0]['voice']) != (b['section'], b['voice']):
                    out.append(cur)
                    cur = []
                cur.append(b)
        if cur:
            out.append(cur)
    return out


def lane_for(sb_path):
    """Lane routing shared by sheets and video — delegates to the project
    lane plugin (core/lane_api), so engine code never names a series.
    Returns the same dict shape builders already consume."""
    import sys as _sys2
    _sys2.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
    import lane_api as _api
    _name, _mod = _api.for_path(sb_path)
    _unit = _mod.unit_id(sb_path)
    return _mod.paths(_vf.repo_root(), _unit)


def drops_for(sb_path):
    """Owner-called impact drops: {bid: {pause, why}}. why is required
    (fail loud) — every silence is justified or it doesn't render."""
    import json, os
    dp = lane_for(sb_path)['drops']
    if not os.path.exists(dp):
        return {}
    d = json.load(open(dp, encoding='utf-8'))
    for bid, spec in d.items():
        assert isinstance(spec, dict) and spec.get('pause', 0) > 0, f"drop {bid}: needs {{pause: seconds}}"
        assert (spec.get('why') or '').strip(), f"drop {bid}: needs a why — unjustified silence never renders"
    return d


def draws_for(sb_path):
    """Owner-called sleepdraws: {start_bid: {asset, complete_bid,
    clear=fade|cut, fade=seconds, why}}. Entry always fades in from white
    between the two onsets (the sleepdraw); clearing is fade to white over
    `fade` seconds (default 1.5) or an instant cut like a crisp boom-white.
    why is required (fail loud) — unjustified motion never renders. Spec
    lives beside the drops file (draws_chNN.json / shiva draws_sNN.json)."""
    import json, os
    lane = lane_for(sb_path)
    dp = os.path.join(os.path.dirname(lane['drops']),
                      os.path.basename(lane['drops']).replace('drops_', 'draws_'))
    if not os.path.exists(dp):
        return {}
    d = json.load(open(dp, encoding='utf-8'))
    for bid, spec in d.items():
        assert isinstance(spec, dict) and spec.get('asset'), f"draw {bid}: needs an asset path"
        assert spec.get('complete_bid'), f"draw {bid}: needs complete_bid (the frame it is complete on)"
        if spec.get('etch'):
            assert os.path.exists(spec['etch']), f"draw {bid}: etch video missing: {spec['etch']}"
        assert spec.get('clear', 'cut') in ('fade', 'cut'), f"draw {bid}: clear is fade|cut"
        assert float(spec.get('fade', 1.5)) > 0, f"draw {bid}: fade seconds must be > 0"
        assert (spec.get('why') or '').strip(), f"draw {bid}: needs a why — unjustified motion never renders"
    return d


def draw_progress(base_im, asset_path, p):
    """Sleepdraw: fade a raster image in from white on a base card.
    p in [0,1] is asset opacity (0 = unstarted white, 1 = complete).
    Clearing reuses this with falling p (fade to white); a cut clearing
    simply stops showing the card like a crisp boom-white. Asset is fitted
    inside the safe zone (85px margins, above SUB_Y) and centered. Single
    source for video sub-frames and the completed card."""
    from PIL import Image
    im = base_im.copy()
    asset = Image.open(asset_path).convert('RGB')
    box_w, box_h = W - 2 * SAFE_MARGIN, SUB_Y - 90
    asset.thumbnail((box_w, box_h), Image.LANCZOS)
    x = (W - asset.size[0]) // 2
    y = 90 + (box_h - asset.size[1]) // 2
    assert_safe(y + asset.size[1], f'draw asset {asset_path}')
    p = min(1.0, max(0.0, p))
    ground = Image.new('RGB', asset.size, LIGHT)
    im.paste(Image.blend(ground, asset, p), (x, y))
    return im


def clips_for(sb_path):
    """Owner-called overlay clips: {start_bid: {asset, complete_bid,
    clear=fade|cut, fade=seconds, why}}. A muted video plays on the mini
    canvas (centered, 1280x660, above subtitles) between the two onsets,
    then its last frame holds like a persist until the next cue/chant/
    tone-break. Audio is NEVER carried (muted by construction — the mix
    stays ours). why is required — unjustified motion never renders. Spec
    lives beside the drops file (clips_chNN.json / shiva clips_sNN.json).
    Used sparingly, for effect."""
    import json, os
    lane = lane_for(sb_path)
    dp = os.path.join(os.path.dirname(lane['drops']),
                      os.path.basename(lane['drops']).replace('drops_', 'clips_'))
    if not os.path.exists(dp):
        return {}
    d = json.load(open(dp, encoding='utf-8'))
    for bid, spec in d.items():
        assert isinstance(spec, dict) and spec.get('asset'), f"clip {bid}: needs an asset mp4 path"
        assert spec.get('complete_bid'), f"clip {bid}: needs complete_bid (span end onset)"
        assert spec.get('clear', 'cut') in ('fade', 'cut'), f"clip {bid}: clear is fade|cut"
        assert float(spec.get('fade', 1.5)) > 0, f"clip {bid}: fade seconds must be > 0"
        assert (spec.get('why') or '').strip(), f"clip {bid}: needs a why — unjustified motion never renders"
    return d


def etch_paste(base_im, frame_im, q=1.0):
    """Paste one pre-rendered full-frame etch frame (1920x1080, already
    negated to ink-on-white at pre-render); q fades it toward white."""
    from PIL import Image
    assert frame_im.size == (W, H), f'etch frame must be {W}x{H}'
    im = base_im.copy()
    if q >= 1.0:
        im.paste(frame_im, (0, 0))
    else:
        ground = Image.new('RGB', frame_im.size, LIGHT)
        im.paste(Image.blend(frame_im, ground, min(1.0, max(0.0, 1.0 - q))), (0, 0))
    return im


def overlay_paste(base_im, frame_im, q=1.0):
    """Paste one pre-rendered canvas frame (exactly CANVAS_W x CANVAS_H)
    centered-safe; q fades it toward white for fade clearings."""
    from PIL import Image
    assert frame_im.size == (CANVAS_W, CANVAS_H), f'canvas frame must be {CANVAS_W}x{CANVAS_H}'
    im = base_im.copy()
    if q >= 1.0:
        im.paste(frame_im, (CANVAS_X, CANVAS_Y))
    else:
        ground = Image.new('RGB', frame_im.size, LIGHT)
        im.paste(Image.blend(frame_im, ground, min(1.0, max(0.0, 1.0 - q))), (CANVAS_X, CANVAS_Y))
    assert_safe(CANVAS_Y + CANVAS_H, 'overlay canvas')
    return im


def split_after(groups, bids):
    """Split render groups after the listed block ids (impact drops).
    Same function in every builder — identical boundaries everywhere."""
    out = []
    for g in groups:
        cur = []
        for b in g:
            cur.append(b)
            if b['id'] in bids:
                out.append(cur)
                cur = []
        if cur:
            out.append(cur)
    return out


def shiva_header(blocks):
    """Sutra intro header — implementation lives in the shiva-sutras lane
    plugin (projects/shiva-sutras/lane.py). Kept here as a thin alias."""
    import sys as _sys3
    _sys3.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
    import lane_api as _api
    return _api.load_lane('shiva-sutras').header(blocks)


def intro_hold(ch, title=None, asset_dir=None, maxbox=(1400, 730), numeral=None,
               center_art=False, header=None):
    """Intro bug shared by sheets and video: per-chapter thumbnail fitted
    above the subtitle zone (maxbox bounds the fit — shiva renders smaller
    for elegance). Numeral top-right unless numeral=False (shiva numerals
    pending owner call) or ch01 blessed reference (thumbnail alone, never
    touched). Art lookup: chNN.png, then series.png, then the legacy
    tantrasara fallback only when asset_dir is None (default lane).
    Returns None when no art exists — caller falls back to first verse."""
    import os
    base = _vf.repo_root()
    tdir = asset_dir or os.path.join(base, 'assets', 'thumbnail')
    tb = os.path.join(tdir, 'ch' + ch + '.png')
    if not os.path.exists(tb):
        tb = os.path.join(tdir, 'series.png')
    if not os.path.exists(tb) and asset_dir is None:
        tb = os.path.join(base, 'assets', 'thumb_ch1.png')  # legacy fallback
    if not os.path.exists(tb):
        return None
    _tb = Image.open(tb).convert('RGB')
    _tb.thumbnail(maxbox, Image.LANCZOS)
    im = Image.new('RGB', (W, H), LIGHT)
    _vy = (H - _tb.height) // 2 if center_art else 50
    im.paste(_tb, ((W - _tb.width) // 2, _vy))
    # mandala clearance, measured from the art itself before any ink lands:
    # saturated pixels only (the paste rect is white-margined). Each ink
    # box is checked against the art rows it actually occupies.
    from PIL import ImageChops
    _sat = im.crop((0, 0, W, H)).convert('HSV').split()[1]
    _mask = _sat.point(lambda v: 255 if v > 30 else 0)
    if numeral is None:
        numeral = ch != '01'
    if numeral:
        d = ImageDraw.Draw(im)
        fnt = F(FE, 150)
        num = ch.zfill(2)
        d.text((W - 120 - d.textlength(num, font=fnt), 60), num, font=fnt, fill=INK)
        if title:
            # canonical header: title top-left + numeral top-right,
            # optically level ink tops (not draw parity): measured off a
            # temp raster of the actual glyphs (deterministic — same
            # fonts in, same pixels out). Deva bearings vary per word;
            # font tables alone cannot level them (ch21 proved it).
            _probe_n = Image.new('RGB', (W, H), LIGHT)
            ImageDraw.Draw(_probe_n).text((0, 0), num, font=fnt, fill=INK)
            _ntop = _probe_n.convert('L').point(lambda v: 0 if v > 200 else 255).getbbox()[1]
            _d0 = F(FD, 84)
            if d.textlength(title['deva'], font=_d0) > 520:
                _d0 = F(FD, 64)
            _probe_d = Image.new('RGB', (W, H), LIGHT)
            ImageDraw.Draw(_probe_d).text((0, 0), title['deva'].split()[0], font=_d0, fill=INK)
            _dtop = _probe_d.convert('L').point(lambda v: 0 if v > 200 else 255).getbbox()[1]
            _gap = max(0, _ntop - _dtop)
            y = 60 + _gap
            y0 = y
            # column width retries: 520 first, then narrower until the
            # stack clears the mandala (law: Deva 84 wherever it fits
            # the mandala bound, 64 as the wrap-down step). Deterministic;
            # the asserts still fail loud if nothing fits.
            _plan = None
            for _maxw in (520, 500, 480, 460):
                _dlines = [title['deva']]
                _df = F(FD, 84)
                if d.textlength(title['deva'], font=_df) > _maxw:
                    _df = F(FD, 64)
                    _parts, _cur = [], ''
                    for w_ in title['deva'].split():
                        _t = (_cur + ' ' + w_).strip()
                        if d.textlength(_t, font=_df) > _maxw and _cur:
                            _parts.append(_cur)
                            _cur = w_
                        else:
                            _cur = _t
                    if _cur:
                        _parts.append(_cur)
                    _dlines = _parts
                _yy, _boxes, _ops = y0, [], []
                _cx = 120 + max(d.textlength(ln, font=_df) for ln in _dlines) / 2
                for ln in _dlines:
                    _ops.append((ln, 120, _yy, _df, INK))
                    _boxes.append((120, _yy, 120 + d.textlength(ln, font=_df),
                                    _yy + int(_df.size * 1.35)))
                    _yy += int(_df.size * 1.35)
                _engw = max(d.textlength(ln, font=_df) for ln in _dlines)
                for txt, fp, fsz, fill in ((title.get('iast', ''), FE, 28, ROMAN_FILL),
                                           (title.get('literal', ''), FR, 24, LIT_FILL),
                                           (title.get('final', ''), FR, 36, FINAL_FILL)):
                    if not txt:
                        continue
                    _gf = F(fp, fsz)
                    for gln in wrap_lines(d, txt, _gf, min(_engw, _maxw)):
                        _lx = _cx - d.textlength(gln, font=_gf) / 2
                        _ops.append((gln, _lx, _yy, _gf, fill))
                        _boxes.append((_lx, _yy, _lx + d.textlength(gln, font=_gf),
                                      _yy + int(fsz * 1.35)))
                        _yy += int(fsz * 1.35)
                _ok = True
                for (x0, y0b, x1, y1) in _boxes:
                    if y1 > SUB_Y:
                        _ok = False
                        break
                    if y0b < 780:
                        _rows = _mask.crop((0, max(0, int(y0b)), W, min(H, int(y1) + 1)))
                        _bb = _rows.getbbox()
                        if _bb is not None and x1 > _bb[0]:
                            _ok = False
                            break
                if _ok:
                    _plan = (_ops, _boxes, _yy)
                    break
            assert _plan is not None, 'title stack fits no column — restyle the title'
            boxes = []
            for (ln, lx, ly, fnt_, fill) in _plan[0]:
                d.text((lx, ly), ln, font=fnt_, fill=fill)
            boxes = _plan[1]
            y = _plan[2]
            # mandala clearance, measured from the art itself: leftmost
            # non-white pixel over the title band rows is the hard bound.
            for (x0, y0b, x1, y1) in boxes:
                assert y1 <= SUB_Y, 'title stack collides with subtitle zone'
                if y0b < 780:
                    _rows = _mask.crop((0, max(0, int(y0b)), W, min(H, int(y1) + 1)))
                    _bb = _rows.getbbox()
                    if _bb is not None:
                        assert x1 <= _bb[0], f'title ink over the mandala ({x1:.0f} vs art {_bb[0]})'
    if header and header.get('ref'):
        # shiva header mirrors the canonical header in the same type:
        # sutra ref top-right (FE 150, numeral's mirror), funny title
        # top-left (FE 64, wrapped clear of the art). Verse hold follows
        # at the chant — ref + funny first, Sanskrit after.
        d = ImageDraw.Draw(im)
        _rf = F(FE, 150)
        d.text((W - 120 - d.textlength(header['ref'], font=_rf), 60),
               header['ref'], font=_rf, fill=INK)
        _hboxes = [((W - 120 - d.textlength(header['ref'], font=_rf)), 60,
                    W - 120, 60 + int(_rf.size * 1.35))]
        if header.get('title'):
            # optical cap-top alignment with the ref numerals: big type
            # carries tall empty bearings, so same-draw-height reads as
            # misaligned (measured 73 vs 139). Shift the title down by the
            # bearing gap, computed from the fonts (deterministic, no raster
            # pass). Tantrasara's blessed pair keeps draw-height parity —
            # this changes shiva only.
            _tf = F(FE, 64)
            _wrapped = wrap_lines(d, header['title'], _tf, 640)
            _ref_top = _rf.getbbox(header['ref'])[1]
            _tit_top = _tf.getbbox(_wrapped[0])[1] if _wrapped else 0
            _hy = 60 + max(0, _ref_top - _tit_top)
            for _tln in _wrapped:
                d.text((120, _hy), _tln, font=_tf, fill=INK)
                _hboxes.append((120, _hy, 120 + d.textlength(_tln, font=_tf),
                                _hy + int(_tf.size * 1.35)))
                _hy += int(_tf.size * 1.35)
        for (x0, y0, x1, y1) in _hboxes:
            assert y1 <= SUB_Y, 'header collides with subtitle zone'
            if y0 < 780:
                _rows = _mask.crop((0, max(0, int(y0)), W, min(H, int(y1) + 1)))
                _bb = _rows.getbbox()
                if _bb is not None:
                    assert x1 <= _bb[0], f'header ink over the art ({x1:.0f} vs art {_bb[0]})'
    return im


def build_holds(blocks):
    """One hold per verse-voiced block (owner call 2026-11-04 — every
    chant gets its own card, including verse-voiced dialogue mantra
    lines that used to play over white); titles/figures solo.
    MAX_PAIRS caps Deva line-pairs rendered per card face."""
    holds = []
    for b in blocks:
        if b['id'] == 'b_opener':
            holds.append([b])
            continue
        if b.get('voice') == 'verse':
            holds.append([b])
            continue
        if b['type'] in ('title', 'figure'):
            holds.append([b])
    return holds


# List screen engine: count decides the shape, positions never move, one
# standard Sanskrit size everywhere (Deva 84 + grey gloss 40 — locked
# 2026-11-04, owner call). 1 centered · 2 side by side · 3 in a row when
# they fit, else triangle (apex + two below) · 4 the corners · 5 corners
# plus middle (newest middle, earlier four in arrival order). Past five
# the window slides and the oldest drops off. Subtitles own y=860 alone.
POS_MIDDLE = {'kind': 'middle', 'y': 400, 'maxw': 1750}
POS_CORNERS = [
    {'kind': 'top-left', 'cx': 510, 'y': 90, 'maxw': 780},
    {'kind': 'top-right', 'cx': 1410, 'y': 90, 'maxw': 780},
    {'kind': 'bottom-left', 'cx': 510, 'y': 620, 'maxw': 780},
    {'kind': 'bottom-right', 'cx': 1410, 'y': 620, 'maxw': 780},
]
POS_PAIR = [{'cx': 560, 'y': 430, 'maxw': 780},
            {'cx': 1360, 'y': 430, 'maxw': 780}]
POS_ROW3 = [{'cx': 400, 'y': 430, 'maxw': 560},
            {'cx': 960, 'y': 430, 'maxw': 560},
            {'cx': 1520, 'y': 430, 'maxw': 560}]
POS_TRI = [{'cx': 960, 'y': 150, 'maxw': 800},
           {'cx': 480, 'y': 520, 'maxw': 640},
           {'cx': 1440, 'y': 520, 'maxw': 640}]
POS_WINDOW = 5  # middle + four corners; longer lists slide the window


def render_list(keys, glossary):
    """Count decides the shape. 1 centered, 2 side by side, 3 row-or-triangle,
    4 corners, 5 corners + middle. Window slides past five."""
    import unicodedata
    im = Image.new('RGB', (W, H), LIGHT)
    d = ImageDraw.Draw(im)
    boxes = []

    def _item(k):
        # display layers from the glossary entry: citation Deva (never the
        # folded key — folding destroys ś/ṣ/ṇ), IAST derived from the Deva,
        # T1-style literal, final gloss. Missing layers render nothing.
        # Gating lives in the glossary dict each caller passes (sheets pass
        # proposed for review; video passes confirmed only).
        v = (glossary or {}).get(k, '')
        if isinstance(v, dict):
            deva = v.get('deva') or to_deva(k)
            gloss = v.get('gloss', '')
            literal = v.get('literal', '')
            if isinstance(gloss, dict):
                gloss = gloss.get('gloss', '')
        else:
            deva, gloss, literal = to_deva(k), (v or ''), ''
        try:
            iast = to_iast(deva)
        except Exception:
            iast = ''
        return deva, iast, literal, gloss

    def _col(cx, y, deva, iast, literal, gloss, maxw,
             DSZ=84, ISZ=32, LSZ=28, FSZ=40):
        # centered column: every layer centered under the Sanskrit above it.
        # Deva steps one size down if it cannot fit the column (verse rule);
        # anything still wider fails loud (owner restyles, never ships tofu).
        sz = DSZ
        lines = wrap_lines(d, deva, F(FD, sz), maxw) or [deva]
        if max(d.textlength(ln, font=F(FD, sz)) for ln in lines) > maxw:
            sz = 64
            raw = wrap_lines(d, deva, F(FD, sz), maxw) or [deva]
            lines = []
            for ln in raw:
                lines.extend(wrap_lines(d, ln, F(FD, sz), maxw) or [ln])
        w = max(d.textlength(ln, font=F(FD, sz)) for ln in lines)
        assert w <= maxw + 2, f'column overflow ({w:.0f}px > {maxw}px) — split or restyle the list'
        x = cx - w / 2
        for ln in lines:
            lx = cx - d.textlength(ln, font=F(FD, sz)) / 2
            d.text((lx, y), ln, font=F(FD, sz), fill=INK)
            y += int(sz * 1.35)
        boxes.append((x, y - sum(int(sz * 1.35) for _ in lines), x + w, y))
        for txt, fp, fsz, fill in ((iast, FE, ISZ, ROMAN_FILL),
                                  (literal, FR, LSZ, LIT_FILL),
                                  (gloss, FR, FSZ, FINAL_FILL)):
            if not txt:
                continue
            for gln in wrap_lines(d, txt, F(fp, fsz), maxw):
                lx = cx - d.textlength(gln, font=F(fp, fsz)) / 2
                d.text((lx, y), gln, font=F(fp, fsz), fill=fill)
                boxes.append((lx, y, lx + d.textlength(gln, font=F(fp, fsz)),
                              y + int(fsz * 1.35)))
                y += int(fsz * 1.35)
        return y

    def _fits_row(items):
        return all(d.textlength(deva, font=F(FD, 84)) <= 560
                   and all(not t or d.textlength(t, font=F(FD if f == FE else FR, s)) <= 560
                           for t, f, s in ((iast, FE, 32), (literal, FR, 28), (gloss, FR, 40)))
                   for deva, iast, literal, gloss in items)

    window = keys[-POS_WINDOW:]
    items = [_item(k) for k in window]
    n = len(items)
    if n == 1:
        _col(W / 2, 380, *items[0], 1750)
    elif n == 2:
        for item, slot in zip(items, POS_PAIR):
            _col(slot['cx'], slot['y'], *item, slot['maxw'])
    elif n == 3:
        slots = POS_ROW3 if _fits_row(items) else POS_TRI
        for item, slot in zip(items, slots):
            _col(slot['cx'], slot['y'], *item, slot['maxw'])
    elif n == 4:
        for item, slot in zip(items, POS_CORNERS):
            _col(slot['cx'], slot['y'], *item, slot['maxw'],
                 84, 28, 24, 36)
    else:
        for item, slot in zip(items[:-1], POS_CORNERS):
            _col(slot['cx'], slot['y'], *item, slot['maxw'],
                 84, 28, 24, 36)
        _col(W / 2, POS_MIDDLE['y'], *items[-1], POS_MIDDLE['maxw'],
             84, 32, 28, 40)
    for (x0, y0, x1, y1) in boxes:
        assert y1 <= SUB_Y, 'conveyor collides with subtitle zone'
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            overlap = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
            assert not overlap, 'conveyor slots overlap — split or restyle the list'
    return im


def to_deva(s):
    import re as _re
    if _re.search(r'[\u0900-\u097F]', s):
        return s  # already Devanagari
    from indic_transliteration.sanscript import transliterate, IAST, DEVANAGARI
    return transliterate(s, IAST, DEVANAGARI)


def split_scripts(t):
    """Devanagari tokens vs roman tokens — never mix scripts on one line
    (M4, promoted from the pilot builder to shared law)."""
    deva, roman = [], []
    for w in t.strip().split():
        c = w.strip('—.,!?;:')
        if not c:
            continue
        (deva if any('\u0900' <= ch <= '\u097f' for ch in c) else roman).append(w.strip('—.,!?;:'))
    return ' '.join(deva), ' '.join(roman)


def to_iast(s):
    import re as _re
    if not _re.search(r'[\u0900-\u097F]', s):
        return s  # already roman
    from indic_transliteration.sanscript import transliterate, DEVANAGARI, IAST
    return transliterate(s, DEVANAGARI, IAST)


def verse_match_key(devanagari_text):
    """Canonical key for a verse block: IAST, folded, alphanumeric only.
    Deterministic across storyboard rebuilds (no positional overrides)."""
    import re as _re, unicodedata
    s = _re.sub(r'\s+', ' ', devanagari_text.strip())
    try:
        s = to_iast(s)
    except Exception:
        pass
    return _re.sub(r'[^a-z]', '', ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'))


def render_term_card(deva, iast, literal, final, DSZ=84, ISZ=32, LSZ=28,
                     FSZ=40):
    """Single centered four-layer term card. Returns the image."""
    im = Image.new('RGB', (W, H), LIGHT)
    d = ImageDraw.Draw(im)
    boxes = []
    lines = wrap_lines(d, deva, F(FD, DSZ), 1750) or [deva]
    total = (sum(int(DSZ * 1.35) for _ in lines)
             + (sum(int(ISZ * 1.35) for _ in wrap_lines(d, iast, F(FE, ISZ), 1750)) if iast else 0)
             + (sum(int(LSZ * 1.35) for _ in wrap_lines(d, literal, F(FR, LSZ), 1750)) if literal else 0)
             + (sum(int(FSZ * 1.35) for _ in wrap_lines(d, final, F(FR, FSZ), 1750)) if final else 0))
    y = max(90, 540 - total // 2 - 40)
    for ln in lines:
        lx = (W - d.textlength(ln, font=F(FD, DSZ))) / 2
        d.text((lx, y), ln, font=F(FD, DSZ), fill=INK)
        boxes.append((lx, y, lx + d.textlength(ln, font=F(FD, DSZ)),
                      y + int(DSZ * 1.35)))
        y += int(DSZ * 1.35)
    for txt, fp, fsz, fill in ((iast, FE, ISZ, ROMAN_FILL),
                              (literal, FR, LSZ, LIT_FILL),
                              (final, FR, FSZ, FINAL_FILL)):
        if not txt:
            continue
        for gln in wrap_lines(d, txt, F(fp, fsz), 1750):
            lx = (W - d.textlength(gln, font=F(fp, fsz))) / 2
            d.text((lx, y), gln, font=F(fp, fsz), fill=fill)
            boxes.append((lx, y, lx + d.textlength(gln, font=F(fp, fsz)),
                          y + int(fsz * 1.35)))
            y += int(fsz * 1.35)
    for (x0, y0, x1, y1) in boxes:
        assert y1 <= SUB_Y, 'term card collides with subtitle zone'
    return im


def wrap_lines(draw, text, font, maxw=1750):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def render_hold(hold, sub_text=None, glossary=None):
    """Verse cards: Deva + IAST per line; single-word glossed chants resolve
    via glossary to the full four term layers. Callers gate: sheets pass
    proposed for review, video passes confirmed only.

    New card types register via register_hold() instead of editing this
    dispatch — sheets and video share them automatically."""
    first = hold[0]
    im = Image.new('RGB', (W, H), LIGHT)
    d = ImageDraw.Draw(im)
    kind = 'opener' if first['id'] == 'b_opener' else first['type']
    if kind in _HOLD_RENDERERS:
        _HOLD_RENDERERS[kind](d, im, hold, sub_text, glossary)
    elif kind == 'opener':
        pass  # clean card under the bell
    elif kind == 'title':
        t = re.sub(r'^\d+\.\s*', '', first['text'])
        fnt = F(FE, 96)
        while d.textlength(t, font=fnt) > 1750 and fnt.size > 40:
            fnt = F(FE, fnt.size - 4)
        ct(d, 430, t, fnt)
    elif kind == 'figure':
        t = first['text']
        m = re.match(r'^#?\s*(\d+)\s*(.*)$', t)
        if m and len(t) < 40:
            ct(d, 360, m.group(1), F(FE, 150))
            if m.group(2).strip():
                ct(d, 580, m.group(2).strip(), F(FE, 44))
        else:
            fnt = F(FE, 72)
            while d.textlength(t, font=fnt) > 1750 and fnt.size > 40:
                fnt = F(FE, fnt.size - 4)
            ct(d, 430, t, fnt)
    else:  # verse: Deva + IAST + T1 literal + L4-or-L3 final, grey ramp down
        import unicodedata
        fold = lambda s: ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
        dl = []
        for b in hold:
            lines = [ln.strip().rstrip('.') for ln in b['text'].strip().splitlines()]
            lines = [s for s in lines if s]
            if not lines:
                continue
            # per-line: lone glossed chants resolve to full term layers;
            # all other verse lines are Devanagari ONLY — subtitles already
            # carry the romanised (owner call 2026-11-04).
            for s in lines:
                deva_part, roman_part = split_scripts(s)
                # lookup by content hash of the Sanskrit half (M12-proof):
                # the author's roman half IS the IAST key; transliterate
                # only where no roman exists. Whole mixed lines never
                # match a folded key (M4 class) — halves do.
                v = (glossary or {}).get(verse_match_key(roman_part or deva_part or s), '')
                single = len(s.split()) <= 3
                if single and isinstance(v, dict) and (v.get('deva') or v.get('gloss') or v.get('literal')):
                    deva = v.get('deva') or to_deva(deva_part or s)
                    gloss = v.get('gloss', '')
                    literal = v.get('literal', '')
                    if isinstance(gloss, dict):
                        gloss = gloss.get('gloss', '')
                    iast = ''
                    if roman_part or deva:
                        try:
                            iast = roman_part or to_iast(deva)
                        except Exception:
                            iast = roman_part
                else:
                    try:
                        deva = to_deva(deva_part or s)
                    except Exception:
                        deva = deva_part or s
                    gloss, literal, iast = '', '', ''
                if d.textlength(deva, font=F(FD, 84)) <= 1700:
                    dl.append({'deva': [(deva, 84)] if deva.strip() else [], 'iast': [iast] if iast else [],
                               'literal': [literal] if literal else [], 'final': [gloss] if gloss else []})
                    continue
                fsmall = F(FD, 64)
                parts, cur = [], ''
                for w_ in deva.split():
                    t = (cur + ' ' + w_).strip()
                    if d.textlength(t, font=fsmall) > 1700 and cur:
                        parts.append(cur)
                        cur = w_
                    else:
                        cur = t
                if cur:
                    parts.append(cur)
                for ln in parts:
                    assert d.textlength(ln, font=fsmall) <= 1780, f'verse overflow: {ln[:40]}'
                dl.append({'deva': [(ln, 64) for ln in parts] if deva.strip() else [], 'iast': [iast] if iast else [],
                           'literal': [literal] if literal else [], 'final': [gloss] if gloss else []})
        lh = lambda sz: int(sz * 1.35)
        total = 0
        for e in dl:
            for _, sz in e['deva']:
                total += lh(sz)
            for _ln in e['iast']:
                total += sum(lh(32) for _ in wrap_lines(d, _ln, F(FE, 32), 1750) or [0])
            for _ln in e['literal']:
                total += sum(lh(28) for _ in wrap_lines(d, _ln, F(FR, 28), 1750) or [0])
            for _ln in e['final']:
                total += sum(lh(40) for _ in wrap_lines(d, _ln, F(FR, 40), 1750) or [0])
            total += 26
        total -= 26
        y = max(90, 540 - total // 2 - 40)
        for e in dl:
            for ln, sz in e['deva']:
                fnt = F(FD, sz)
                assert d.textlength(ln, font=fnt) <= 1780, f'verse overflow: {ln[:40]}'
                d.text(((W - d.textlength(ln, font=fnt)) / 2, y), ln, font=fnt, fill=INK)
                y += lh(sz)
            for txts, fp, fsz, fill in ((e['iast'], FE, 32, ROMAN_FILL),
                                       (e['literal'], FR, 28, LIT_FILL),
                                       (e['final'], FR, 40, FINAL_FILL)):
                for t0 in txts:
                    if not t0:
                        continue
                    for gln in wrap_lines(d, t0, F(fp, fsz), 1750):
                        lx = (W - d.textlength(gln, font=F(fp, fsz))) / 2
                        d.text((lx, y), gln, font=F(fp, fsz), fill=fill)
                        y += lh(fsz)
            y += 26
        assert y - 26 <= SUB_Y, 'card collides with subtitle zone — split the stack'
    if sub_text:
        fnt = F(FE, 46)
        wrapped = wrap_lines(d, sub_text, fnt)
        if len(wrapped) > 2:
            fnt = F(FE, 40)
            wrapped = wrap_lines(d, sub_text, fnt)
        assert len(wrapped) <= 2, 'subtitle too long'
        for i, ln in enumerate(wrapped):
            d.text(((W - d.textlength(ln, font=fnt)) / 2, SUB_Y + i * 62), ln, font=fnt, fill=INK)
    return im
