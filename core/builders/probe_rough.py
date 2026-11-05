#!/usr/bin/env python3
"""Rough-part audio probes: storyboard → suspect clips → ears/Qwen.
Usage: python3 probe_rough.py <storyboard.json> <outdir> [--limit N]
Picks the blocks Fish is likeliest to mangle (IAST diacritics, digits,
heavy punctuation, short fragments, ALLCAPS, mixed scripts), voices
each with its own seat via Fish, whisper-transcribes, and scores the
folded round-trip. Suspects (score<0.6) go to owner ears + Qwen;
punctuation-heavy blocks are ear-listed always (TTS pauses are not
machine-provable). Cache: /tmp/probes/<hash>.wav (reproducible).
Step 2 of the canonical flow: storyboard → rough probes → chapter
audio → visuals.
"""
import json, os, re, sys, hashlib, subprocess, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf

BASE = os.path.dirname(os.path.abspath(__file__))
PROBE_DIR = '/tmp/probes'
VOICES = _vf.voices()


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def rough_score(block):
    """Higher = likelier to mangle. Verse+diacritics top, then fragments."""
    t = block['text']
    s = 0
    if re.search(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṂḤṄÑṬḌṆŚṢ]', t):
        s += 3
    if re.search(r'[\u0900-\u097F]', t):
        s += 2 if block['voice'] != 'verse' else 1
    if re.search(r'\d', t):
        s += 2
    if len(re.findall(r'[;:"—()…/]', t)) >= 2:
        s += 2
    if len(t.split()) <= 4:
        s += 2
    if re.search(r'\b[A-Z]{2,}\b', t):
        s += 1
    if block['voice'] == 'verse' and len(t.split()) > 6:
        s += 1
    return s


def main():
    sb_path, outdir = sys.argv[1], sys.argv[2]
    lim = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 25
    sb = json.load(open(sb_path, encoding='utf-8'))
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(PROBE_DIR, exist_ok=True)
    cands = [b for b in sb['blocks']
             if b.get('voice') in VOICES and b['id'] != 'b_opener']
    ranked = sorted(((rough_score(b), b['id'], b) for b in cands), reverse=True)
    ranked = [(s, b) for s, _, b in ranked if s > 0][:lim]
    print(f'probing {len(ranked)} rough blocks')
    from faster_whisper import WhisperModel
    model = WhisperModel('base')
    report, suspects, earlist = [], [], []
    for score, b in ranked:
        h = hashlib.sha1(f"{b['voice']}|{b.get('directed', b['text'])}".encode()).hexdigest()[:12]
        wav = f'{PROBE_DIR}/{b["id"]}_{h}.wav'
        if not (os.path.exists(wav) and os.path.getsize(wav) > 1000):
            r = subprocess.run(
                ['python3', _vf.tts_script(),
                 b.get('directed', b['text']), wav, '1.0', VOICES[b['voice']]],
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0 or not os.path.exists(wav):
                report.append({'bid': b['id'], 'status': 'TTS-FAIL'})
                continue
        heard = ' '.join(s.text for s in model.transcribe(wav)[0]).lower()
        hn = re.sub(r'[^a-z ]', '', heard).split()
        want = [re.sub(r'[^a-z]', '', x.lower()) for x in b['text'].split()]
        want = [x for x in want if x]
        # Whisper garbles short Sanskrit by design (M37): score the
        # round-trip only on English-dominant blocks; Sanskrit-dominant
        # ones go to ears always (MMS means at video stage corroborate).
        _sans = len(re.findall(r'[āīūṛṝḷṃḥṅñṭḍṇśṣĀĪŪṚṂḤṄÑṬḌṆŚṢ\u0900-\u097F]', b['text']))
        _nwant = len(want)
        if _sans * 3 >= _nwant:
            rec = {'bid': b['id'], 'voice': b['voice'], 'score': score,
                   'roundtrip': 'ears-only (Sanskrit-dominant)',
                   'wav': wav, 'text': b['text'][:120]}
            report.append(rec)
            suspects.append(rec)
            continue
        pos, hit = -1, 0
        for w in want:
            try:
                pos = hn.index(w, pos + 1)
                hit += 1
            except ValueError:
                pass
        ratio = round(hit / max(1, len(want)), 2)
        rec = {'bid': b['id'], 'voice': b['voice'], 'score': score,
               'roundtrip': ratio, 'wav': wav,
               'text': b['text'][:120]}
        report.append(rec)
        if ratio < 0.6:
            suspects.append(rec)
        if len(re.findall(r'[;:"—()…]', b['text'])) >= 2:
            earlist.append(b['id'])
    json.dump(report, open(os.path.join(outdir, 'rough.json'), 'w'), indent=1)
    with open(os.path.join(outdir, 'rough.md'), 'w', encoding='utf-8') as f:
        f.write(f'# Rough probes — {len(report)} clips, {len(suspects)} suspects\n\n')
        for r in suspects:
            f.write(f"- SUSPECT {r['bid']} [{r['voice']}] roundtrip {r['roundtrip']}: {r['text']}\n")
        if earlist:
            f.write(f"\nPunctuation watch (ears always): {', '.join(earlist)}\n")
    print(f'suspects={len(suspects)} earlist={len(earlist)} -> {outdir}/rough.md')
    for r in suspects:
        print(f"  SUSPECT {r['bid']} {r['roundtrip']}: {r['text'][:80]}")


if __name__ == '__main__':
    main()
