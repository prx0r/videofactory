#!/usr/bin/env python3
"""Storyboard builder + validator for Tantrasara explained chapters.
Usage: python3 build_storyboard.py <chapter.md> <out.json>
Parses markdown into blocks, casts a voice per block, validates.
Voice seats (locked 2026-11-02):
  granny = 614f8afd83f841048c040b2c6234d2c1 (main narration)
  man    = fcfd5ebf496949ed9f76b3a533ee4738 (skeptic + dialogue)
  verse  = 4e873c37d4cb439e9bccc4dc1f633290 (Sanskrit + verses)
  none   = visual-only (figures, meta)
"""
import json, re, sys
import os as _os
_sys_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'contract')
if _sys_path not in sys.path:
    sys.path.insert(0, _sys_path)
import paths as _vf

DEVA = re.compile(r'[\u0900-\u097F]')
DEVA_L = re.compile(r'[\u0905-\u0939\u093E-\u094D\u0958-\u0963]')  # letters only: digits never voice a block
URL = re.compile(r'https?://|[\w-]+\.(?:de|com|org|net|info|github\.io)\b')
WITNESS_LBL = re.compile(r'^[A-Z][A-Z0-9 \-,–—\'().;/]*$')
WITNESS_W = ('GRETIL', 'ATTESTED', 'WITNESS', 'TRANSCRIPTION', 'MANUSCRIPT')
IAST = re.compile(r'[āīūṛṝḷḹṃḥṅñṭḍṇśṣĀĪŪṚṜḶṂḤṄÑṬḌṆŚṢ]')
QUOTED = re.compile(r'^["\u201c\u201d]')

# ASCII Sanskrit forms (no diacritics to detect). Grows deliberately per
# chapter: validator ERRORS on short unclassified paragraphs to force this.
SANSKRIT_LEXICON = {
    'krama', 'akrama', 'nimesha', 'unmesha', 'sandra', 'spanda',
    'prana', 'apana', 'samana', 'udana', 'vyana',
}

# Direction tags (Fish free-model native, cf. damn/docs/drama-syntax.md).
# Inserted BEFORE anchors only; body words never rewritten. Allowlist only.
DIRECT_TAGS = {'long pause', 'short pause', 'soft pause', 'slowly', 'calm'}

# Chapter opener: vatulanatha kit logic, free-only. One bell at the head
# of every chapter — bell_ding (0.99s attention grab), +6 dB at mix.
# Kit stays in vatulanatha (single source); pipeline only references it.
OPENER_ASSET = _vf.bell()
TAG_RE = re.compile(r'\[([^\]]{1,40})\]')

def apply_direction(block):
    """Prefix deterministic direction per block type. Returns directed text."""
    t, typ, voice = block['text'], block['type'], block['voice']
    if typ == 'verse' and voice == 'verse':
        return '[slowly] ' + t
    if typ == 'title':
        return '[long pause] ' + t
    if typ == 'dialogue':
        return '[short pause] ' + t
    if typ == 'narration' and is_beat(t):
        return '[short pause] ' + t
    return t

def audit_direction(directed, original):
    """Body integrity: stripped directed text must equal original exactly."""
    stripped = TAG_RE.sub('', directed).strip()
    stripped = re.sub(r'\s+', ' ', stripped)
    orig = re.sub(r'\s+', ' ', original.strip())
    tags = TAG_RE.findall(directed)
    unknown = [g for g in tags if g not in DIRECT_TAGS]
    return stripped == orig, unknown

# Granny's catchwords: interjections and punch lines that earn a beat.
# Curated deliberately per chapter (cf. SANSKRIT_LEXICON). Ordinary short
# sentences ("A human.", "Events happen.") are NOT beats — tagging them all
# turns direction into wallpaper.
BEAT_LEXICON = {
    'right', 'right then', 'yes', 'good', 'lovely stuff',
    'absolutely not', 'absolutely bloody not', 'absolutely useless',
    'absolutely beautiful', 'time', 'precisely', 'magnificent', 'mate',
    'quite', 'thank goodness', 'excellent', 'very depressing', 'now',
    'indeed', 'exactly', 'lovely', 'correct',
    'now, hold on', 'no, not like that',
}

def is_beat(t):
    s = t.strip().lower().rstrip('.!?:;')
    return s in BEAT_LEXICON or t.strip().endswith(':')


def is_provenance(p):
    """Source notes, not story: never voiced, always a held card or nothing."""
    s = p.strip()
    _trans = ('transmitted', 'transcription', 'edition', 'witness', 'GRETIL',
              'variant', 'concluding metrical')
    if s.startswith(('This verse', 'These verses', 'There is no separate', 'No separate')):
        return any(w in s for w in _trans)
    return (s.startswith(('Textual basis', 'Source note', 'Sources:', 'Textual sources'))
            or 'Attachment' in s
            or ('creative' in s and 'retelling' in s and 'exact words' in s))


def is_standalone_sanskrit(p):
    """A paragraph that IS Sanskrit, not a sentence containing it.
    EVERY token must be Sanskrit (diacritic or lexicon) — one English
    word ('Last chapter we discussed X') keeps it with granny.
    Inline mid-sentence terms stay with the host block by construction
    (we never split paragraphs) — granny reads those in flow."""
    words = re.findall(r"[A-Za-zāīūṛṝḷḹṃḥṅñṭḍṇśṣ·\-']+", p)
    if not words or len(words) > 6:
        return False
    for w in words:
        c = w.strip("·-'.,:;!?")
        if not c:
            return False
        if IAST.search(c):
            continue
        if c.lower() in SANSKRIT_LEXICON:
            continue
        return False
    return True

def classify(para, in_translit=False, section=""):
    p = para.strip()
    if not p:
        return None
    if p.startswith(('![', '[image]', 'Textual basis:')):
        return ('meta', 'none')
    if p.startswith('Next:'):
        return ('trailer', 'granny')
    if p in ('ORIGINAL SANSKRIT', 'TRANSLITERATION'):
        return ('label', 'none')
    if re.match(r'^#\s*\d+\s*$', p):
        return ('figure', 'none')
    if len(p) < 60 and p == p.upper() and re.search(r'[A-Z]{2,}', p):
        return ('figure', 'none')
    if DEVA_L.search(p):
        return ('verse', 'verse')
    if QUOTED.match(p):
        return ('dialogue', 'man')
    return ('narration', 'granny')

def build(md_path, overrides=None):
    overrides = overrides or {}
    lines = open(md_path, encoding='utf-8').read().split('\n')
    # title = first '# ' line
    title = next((l[2:].strip() for l in lines if l.startswith('# ')), 'untitled')
    blocks, section, buf, sec_idx = [], 'intro', [], 0
    in_translit = False
    def flush():
        nonlocal buf, in_translit
        out = []
        for para in buf:
            kind = para.get('kind')
            if kind == 'label':
                in_translit = (para['text'] == 'TRANSLITERATION')
                out.append(para)
                continue
            if in_translit and kind in ('narration',):
                # IAST transliteration lines following the label -> verse voice
                if IAST.search(para['text']) or DEVA_L.search(para['text']):
                    para['type'], para['voice'] = 'verse', 'verse'
                elif len(para['text']) < 120:
                    para['type'], para['voice'] = 'verse', 'verse'
                else:
                    in_translit = False
            out.append(para)
        buf.clear()
        return out
    paras, cur = [], []
    for l in lines:
        if l.startswith('## ') or (l.startswith('# ') and not l.startswith('### ')):
            if cur:
                paras.append(('\n'.join(cur), False)); cur = []
            paras.append((re.sub(r'^#{1,2} ', '', l).strip(), True))
        elif l.strip() == '':
            if cur:
                paras.append(('\n'.join(cur), False)); cur = []
        else:
            cur.append(l)
    if cur:
        paras.append(('\n'.join(cur), False))
    bid = 0
    blocks = [{'id': 'b_opener', 'section': 'opener',
               'type': 'opener', 'voice': 'none',
                       'text': '[bell_ding]',
               'asset': OPENER_ASSET, 'mix': '+6dB at mix, voice beds under decay tail'}]
    bid = 1
    for text, is_head in paras:
        text = text.strip()
        if not text or text.startswith('# ') or text.startswith(('![', '[image]')) and len(text) < 200:
            if text.startswith(('[image]', '![')):
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'meta', 'voice': 'none', 'text': text[:120]})
                bid += 1
            continue
        # embedded witness label ("ATTESTED PRAKRIT VERSE — 21.10, GRETIL"):
        # never spoken; head classifies normally, label goes meta
        if '\n' in text:
            split = [seg.strip() for seg in text.split('\n') if seg.strip()]
            lbl = [seg for seg in split if WITNESS_LBL.match(seg) and len(seg) < 120
                   and any(w in seg for w in WITNESS_W)]
            if lbl:
                for seg in lbl:
                    blocks.append({'id': f'b{bid}', 'section': section, 'type': 'meta', 'voice': 'none', 'text': seg})
                    bid += 1
                head = '\n'.join(seg for seg in split if seg not in lbl)
                if not head:
                    continue
                text = head
        if is_head:
            section = text[:60]
            sec_idx += 1
            if DEVA_L.search(text):
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'verse', 'voice': 'verse', 'text': text})
            elif re.match(r'^#?\s*\d+\s*[a-z\u0100-\u024f]*$', text, re.I) and len(text) < 30:
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'figure', 'voice': 'none', 'text': text})
            else:
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'title', 'voice': 'granny', 'text': text})
            bid += 1
            continue
        if text in ('ORIGINAL SANSKRIT', 'TRANSLITERATION'):
            blocks.append({'id': f'b{bid}', 'section': section, 'type': 'label', 'voice': 'none', 'text': text})
            bid += 1
            in_translit = (text == 'TRANSLITERATION')
            continue
        if in_translit:
            # run continues ONLY on Sanskrit lines; an ASCII-only line ends
            # the run and classifies normally (translation gloss in English
            # belongs to granny — edge case #9, verified ch6)
            if IAST.search(text) or DEVA_L.search(text):
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'verse', 'voice': 'verse', 'text': text})
                bid += 1
                continue
            in_translit = False
        if is_provenance(text):
            blocks.append({'id': f'b{bid}', 'section': section, 'type': 'meta', 'voice': 'none', 'text': text})
            bid += 1
            continue
        if URL.search(text) and not DEVA_L.search(text):
            # citation-only line ("GRETIL, Chapter 13.52–53. gretil.sub..."):
            # a spoken URL is never teaching; filed source note carries it
            bare = URL.sub('', text)
            if len(re.findall(r'[A-Za-zāīūṛṝḹṃḥṅñṭḍṇśṣ]+', bare)) < 10:
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'meta', 'voice': 'none', 'text': text})
                bid += 1
                continue
        if re.match(r'^#\s*\d+\s*$', text):
            blocks.append({'id': f'b{bid}', 'section': section, 'type': 'figure', 'voice': 'none', 'text': text})
            bid += 1
            continue
        if len(text) < 60 and text == text.upper() and re.search(r'[A-Z]{2,}', text):
            # shouted punchlines stay spoken: a multi-word sentence ending
            # in a period with no digits, dashes or slashes is granny-grade
            # prose, not a witness label (M-edge-8: silent shouts). Witness
            # labels always carry digits, dashes or slashes — proven by
            # byte-identical rebuild of all frozen tantrasara storyboards.
            bare = text.rstrip('"“” \t')
            if (bare.endswith('.') and len(text.split()) > 1
                    and not re.search(r'[\d—\-/]', text)):
                pass  # falls through to voice casting below
            else:
                blocks.append({'id': f'b{bid}', 'section': section, 'type': 'figure', 'voice': 'none', 'text': text})
                bid += 1
                continue
        if DEVA_L.search(text):
            blocks.append({'id': f'b{bid}', 'section': section, 'type': 'verse', 'voice': 'verse', 'text': text})
            bid += 1
            continue
        if QUOTED.match(text):
            bid_str = f'b{bid}'
            if 'Abhinav' in text:
                # The skeptic addresses Abhinava directly -> man. Holds 5/5 in ch6.
                blocks.append({'id': bid_str, 'section': section, 'type': 'dialogue', 'voice': 'man', 'text': text})
            elif bid_str in overrides:
                blocks.append({'id': bid_str, 'section': section, 'type': 'dialogue', 'voice': overrides[bid_str], 'text': text})
            else:
                blocks.append({'id': bid_str, 'section': section, 'type': 'dialogue', 'voice': 'UNCAST', 'text': text})
            bid += 1
            continue
        if is_standalone_sanskrit(text):
            blocks.append({'id': f'b{bid}', 'section': section, 'type': 'verse', 'voice': 'verse', 'text': text})
            bid += 1
            continue
        blocks.append({'id': f'b{bid}', 'section': section, 'type': 'narration', 'voice': 'granny', 'text': text})
        bid += 1
    for b in blocks:
        if b['id'] in overrides and b['id'] != 'b_opener':
            v = overrides[b['id']]
            assert v in ('granny', 'man', 'verse'), f"override {b['id']}: bad voice {v}"
            # explicit owner call wins (even over the Abhinav-man convention).
            # retype verse<->non-verse so cards follow the voice: the verse
            # seat chants verses; everything granny/man speaks is narration
            # (or dialogue when quote-led).
            if b['type'] == 'verse' and v != 'verse' and not QUOTED.match(b['text'].strip()):
                b['type'] = 'narration'
            b['voice'] = v
    return {'title': title, 'blocks': blocks}

def validate(sb):
    errs, warns = [], []
    by_sec = {}
    for b in sb['blocks']:
        by_sec.setdefault(b['section'], []).append(b)
        if not b['text'].strip():
            errs.append(f"{b['id']}: empty text")
            continue
        if b['id'] == 'b_opener':
            import os as _os
            if b.get('type') != 'opener' or b.get('voice') != 'none':
                errs.append('b_opener: must be type opener, voice none')
            if not b.get('asset') or not _os.path.exists(b['asset']):
                errs.append(f"b_opener: kit asset missing: {b.get('asset')}")
            continue
        if b['voice'] == 'UNCAST':
            errs.append(f"{b['id']}: quote needs casting decision — add to overrides [{b['text'][:60]}]")
            continue
        if b['voice'] not in ('granny', 'man', 'verse', 'none'):
            errs.append(f"{b['id']}: bad voice {b['voice']}")
            continue
        b['directed'] = apply_direction(b)
        ok, unknown = audit_direction(b['directed'], b['text'])
        if not ok:
            errs.append(f"{b['id']}: direction rewrote body words")
        if unknown:
            errs.append(f"{b['id']}: unknown direction tags {unknown}")
        if b['voice'] == 'verse' and not (DEVA.search(b['text']) or IAST.search(b['text']) or b['type'] == 'verse'):
            warns.append(f"{b['id']}: verse voice on non-Sanskrit [{b['text'][:60]}]")
        if b['type'] == 'dialogue' and not QUOTED.match(b['text'].strip()):
            warns.append(f"{b['id']}: dialogue not quote-led [{b['text'][:60]}]")
        if b['type'] == 'narration' and QUOTED.match(b['text'].strip()):
            errs.append(f"{b['id']}: quote-led paragraph cast as narration, must be dialogue [{b['text'][:60]}]")
    for sec, bs in by_sec.items():
        if sec != 'opener' and not any(b['voice'] == 'granny' for b in bs):
            warns.append(f"section [{sec[:40]}]: no granny block")
    return errs, warns

def main():
    md, out = sys.argv[1], sys.argv[2]
    ov_path = sys.argv[3] if len(sys.argv) > 3 else None
    overrides = json.load(open(ov_path, encoding='utf-8')) if ov_path else {}
    sb = build(md, overrides)
    errs, warns = validate(sb)
    words = {}
    for b in sb['blocks']:
        words[b['voice']] = words.get(b['voice'], 0) + len(b['text'].split())
    sb['totals'] = {'blocks': len(sb['blocks']),
                    'words_per_voice': words,
                    'est_min': {k: round(v / 150, 1) for k, v in words.items()}}
    sb['validation'] = {'errors': errs, 'warnings': warns}
    json.dump(sb, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"blocks={len(sb['blocks'])} words={words}")
    print(f"errors={len(errs)} warnings={len(warns)}")
    for e in errs:
        print('ERR', e)
    for w in warns[:20]:
        print('WARN', w)

if __name__ == '__main__':
    main()
