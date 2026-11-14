#!/usr/bin/env python3
"""Render a chapter's audio from its frozen storyboard. Idempotent and $0-safe.
Usage: python3 render_chapter.py <storyboard.json> [--dry-run] [--force] [--limit N]
Layout (all on the volume mount — local disk stays out of it):
  renders/<ch>/groups/<sec>/g<k>_<voice>_<hash>.wav   one Fish call per group
  renders/<ch>/blocks/<bid>.json                      group->block timing map
  renders/<ch>/assembly/<ch>_full.wav                 bell + sections + gaps
  renders/<ch>/receipts/calls.jsonl                   every Fish call logged
Grouping: consecutive blocks, same section, same voice (voice none skipped —
figures/labels are visual-only, narration covers them). Opener bell is an
asset copy, never a render.
Cache: group filename carries sha1(voice+directed text); skip if present
unless --force. --dry-run prints the plan + char usage, calls nothing.
"""
import json, os, re, sys, hashlib, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
from holds import drops_for, split_after, split_phoneme_groups, human_phoneme_key, PHONEMES, PHONEME_DIR, VOICE_DB

VOL = _vf.renders_root()
SECTION_GAP_S = 1.0   # silence between sections (ear review)
BELL_MIX_DB = 6.0     # bell_ding; owner call 2026-11-02: short bell, +6dB
MAN_ATTEN = 0.75      # man reads at 75% amplitude of granny/verse (-2.5 dB)

def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40]

def main():
    sb_path, args = sys.argv[1], sys.argv[2:]
    dry = '--dry-run' in args
    force = '--force' in args
    limit = int(args[args.index('--limit') + 1]) if '--limit' in args else 0
    import gates as _g
    import factory_contract as _fc
    # ONE render gate (owner order 2026-11-06): green storyboard + owner
    # approval. Everything else (review pack, source rebuild, planning
    # gate, free-tier pin) is advisory/record-only — it prints, it never
    # holds the line up.
    if dry:
        _g.entry_check('render', 'storyboard', _fc.validate_bundle, sb_path)
    else:
        _g.entry_check('render', 'storyboard', _fc.validate_storyboard_gate, sb_path)
        _g.advisory('render', 'review-pack', _fc.require_current_review_pack, sb_path)
        _g.advisory('render', 'source', _fc.verify_storyboard_source, sb_path)
        _g.advisory('render', 'storyboard-gate', _fc.require_storyboard_gate, sb_path)
        _g.advisory('render', 'free-tier', _fc.require_free_tier)
    sb = json.load(open(sb_path, encoding='utf-8'))
    ch = slug(sb.get('title', 'chapter')) or 'chapter'
    groups, cur = [], []
    def flush():
        nonlocal cur
        if cur:
            groups.append(cur)
            cur = []
    for b in sb['blocks']:
        if b['id'] == 'b_opener':
            flush()
            groups.append([dict(b, group_kind='opener')])
            continue
        if b['voice'] == 'none' or b.get('type') in ('figure', 'label', 'meta'):
            continue  # visual-only; narration covers it
        key = (b['section'], b['voice'])
        if cur and (cur[0]['section'], cur[0]['voice']) != key:
            flush()
        cur.append(b)
    flush()
    groups = split_phoneme_groups(groups)
    # impact drops split groups so pauses land anywhere (re-rendered halves
    # are content-hash cache misses — automatic, prosody-safe by bed)
    _drops = drops_for(sb_path)
    if _drops:
        _have = {b['id'] for g in groups for b in g if 'group_kind' not in b}
        for _bid in _drops:
            assert _bid in _have, f"drop {_bid}: block not rendered (skipped type?)"
        groups = split_after(groups, set(_drops))
        print(f'impact splits at: {sorted(set(_drops))}', flush=True)
    print(f'chapter={ch} groups={len(groups)}')
    total_chars, n_calls, skipped = 0, 0, 0
    plan = []
    sec_seen, sec_slug = {}, {}
    for b in sb['blocks']:
        if b['section'] not in sec_seen:
            sec_seen[b['section']] = len(sec_seen)
    for sec in sec_seen:
        sec_slug[sec] = slug(sec) or f"sec{sec_seen[sec]:02d}"
    for i, g in enumerate(groups):
        if g[0].get('group_kind') == 'opener':
            plan.append({'kind': 'opener', 'asset': g[0]['asset']})
            continue
        voice, sec = g[0]['voice'], g[0]['section']
        text = ' '.join(b.get('directed', b['text']) for b in g)
        h = hashlib.sha1(f'{voice}|{text}'.encode()).hexdigest()[:12]
        gdir = f'{VOL}/{ch}/groups/{sec_slug[sec]}'
        fn = f'{gdir}/g{i:03d}_{voice}_{h}.wav'
        # cache by content hash, never by positional index: drop splits
        # shift every downstream index, so an index-path hit check would
        # re-render the world. Glob the hash like every other builder.
        import glob as _gg
        _hit = [f for f in _gg.glob(f'{gdir}/*_{voice}_{h}.wav')
                if os.path.getsize(f) > 1000]
        exists = bool(_hit)
        if exists:
            fn = _hit[0]
        # human phonemes (owner call 2026-11-04): a singleton verse
        # group sounding one mapped phoneme uses the human clip, always
        # (re)writes its file (replacing any Fish cache), never the API.
        _human = (len(g) == 1 and g[0]['voice'] == 'verse' and
                  human_phoneme_key(g[0]))
        if _human:
            n_calls += 1
            plan.append({'kind': 'human', 'file': fn, 'voice': voice,
                         'chars': len(text), 'bids': [b['id'] for b in g],
                         'text': text, 'phoneme': _human})
            continue
        total_chars += len(text)
        if exists and not force:
            skipped += 1
            plan.append({'kind': 'cached', 'file': fn, 'bids': [b['id'] for b in g]})
        else:
            n_calls += 1
            plan.append({'kind': 'render', 'file': fn, 'voice': voice,
                         'chars': len(text), 'bids': [b['id'] for b in g],
                         'text': text})
        if limit and n_calls >= limit:
            break
    print(f'tts calls: {n_calls} new, {skipped} cached, {total_chars} chars total')
    for p in plan:
        if p['kind'] == 'human':
            print(f"  HUMAN {p['file']} [{p['phoneme']}] {p['bids'][0]}")
        elif p['kind'] == 'render':
            print(f"  RENDER {p['file']} [{p['voice']}] {p['chars']}ch {p['bids'][0]}..{p['bids'][-1]}")
        elif p['kind'] == 'cached':
            print(f"  cached {p['file']}")
        else:
            print(f"  opener {p['asset']}")
    if dry:
        print(f'DRY RUN — no API calls, est. {total_chars} Fish chars (~${total_chars * 0:.2f} on free tier)')
        return
    # real render: one Fish call per uncached group, receipts appended, failures logged
    VOICES = _vf.voices()
    import hashlib as _hl
    import time as _time
    def _mkdirs(_d):
        # volume mount flakes under load — retry, never crash the run
        for _t in range(4):
            try:
                os.makedirs(_d, exist_ok=True)
                return True
            except OSError:
                _time.sleep(2 * (_t + 1))
        return False
    rdir = f'{VOL}/{ch}/receipts'
    assert _mkdirs(rdir), f'receipts dir unwritable after retries: {rdir}'
    log = open(f'{rdir}/calls.jsonl', 'a', encoding='utf-8')
    done, failed = 0, []
    for p in plan:
        if p['kind'] == 'human':
            if not _mkdirs(os.path.dirname(p['file'])):
                failed.append(p['file'])
                print(f'FAIL {p["file"]}: groups dir unwritable (mount flake)', flush=True)
                continue
            _clip = os.path.join(PHONEME_DIR, PHONEMES[p['phoneme']])
            if not os.path.exists(_clip):
                # deterministic data gap — log it, render everything
                # else, never crash the run (2026-11-05 resilience)
                failed.append(p['file'])
                print(f'FAIL {p["file"]}: human clip missing: {_clip}', flush=True)
                continue
            _det = subprocess.run(
                ['ffmpeg', '-nostats', '-v', 'info', '-i', _clip,
                 '-af', 'volumedetect', '-f', 'null', '-'],
                capture_output=True, text=True)
            import re as _re2
            _me = _re2.search(r'mean_volume: ([\-\d.]+) dB', _det.stderr)
            _mx = _re2.search(r'max_volume: ([\-\d.]+) dB', _det.stderr)
            _gain = 10 ** ((VOICE_DB - float(_me.group(1))) / 20) if _me else 1.0
            if _mx:
                _peak = float(_mx.group(1)) + 20 * __import__('math').log10(_gain)
                if _peak > -1.0:
                    _gain *= 10 ** ((-1.0 - _peak) / 20)
            r = subprocess.run(
                ['ffmpeg', '-y', '-v', 'error', '-i', _clip,
                 '-ar', '44100', '-ac', '1', '-af', f'volume={_gain:.4f}',
                 p['file']], capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(p['file']):
                dur = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=nw=1:nk=1', p['file']],
                    capture_output=True, text=True).stdout.strip()
                try:
                    log.write(json.dumps({'file': p['file'], 'voice': p['voice'],
                                       'chars': p['chars'], 'bids': p['bids'],
                                       'sha': _hl.sha256(open(p['file'], 'rb').read()).hexdigest()[:16],
                                       'dur': dur, 'src': 'human',
                                       'phoneme': p['phoneme'],
                                       'clip': PHONEMES[p['phoneme']],
                                       'gain_db': round(20 * __import__('math').log10(_gain), 1) if _gain > 0 else 0}) + '\n')
                    log.flush()
                except OSError as _oe:
                    print(f'WARN {p["file"]}: receipt unwritten ({_oe}), wav kept', flush=True)
                done += 1
                print(f'human {done} {p["file"]} [{p["phoneme"]}] {dur}s', flush=True)
            else:
                failed.append(p['file'])
                print(f'FAIL {p["file"]}: {r.stderr[-300:]}', flush=True)
            continue
        if p['kind'] != 'render':
            continue
        if not _mkdirs(os.path.dirname(p['file'])):
            failed.append(p['file'])
            print(f'FAIL {p["file"]}: groups dir unwritable (mount flake)', flush=True)
            continue
        try:
            r = subprocess.run(
                ['python3', _vf.tts_script(),
                 p['text'], p['file'], '1.0', VOICES[p['voice']]],
                capture_output=True, text=True, timeout=1200)
        except subprocess.TimeoutExpired:
            # a hung Fish call must not kill a 48-minute run (ch16/ch17
            # 2026-11-05) — record it, render everything else, driver
            # retries the chapter and the cache keeps all progress.
            # 1200s: a ~5-minute intro block (n01 b1-b50) legitimately runs
            # >300s of audio, so the old 300s cap false-failed it.
            failed.append(p['file'])
            print(f'FAIL {p["file"]}: TTS call hung past 1200s, skipped', flush=True)
            continue
        if r.returncode == 0 and os.path.exists(p['file']):
            dur = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=nw=1:nk=1', p['file']],
                capture_output=True, text=True).stdout.strip()
            rec = {'file': p['file'], 'voice': p['voice'], 'chars': p['chars'],
                     'bids': p['bids'], 'src': 'fish',
                     'sha': _hl.sha256(open(p['file'], 'rb').read()).hexdigest()[:16],
                     'dur': dur}
            try:
                log.write(json.dumps(rec) + '\n')
                log.flush()
            except OSError as _oe:
                # receipt lost to a mount flake — the wav itself is the
                # cache (hash + size check), so count it, say so loudly
                print(f'WARN {p["file"]}: receipt unwritten ({_oe}), wav kept', flush=True)
            done += 1
            print(f'ok {done} {p["file"]} {dur}s', flush=True)
        else:
            failed.append(p['file'])
            print(f'FAIL {p["file"]}: {r.stderr[-300:] or r.stdout[-300:]}', flush=True)
    print(f'rendered={done} failed={len(failed)}')
    for f in failed:
        print('FAILED:', f)
    # nonzero while anything is missing so the driver retries the
    # chapter — but every renderable group is already cached, so each
    # attempt makes max progress and transient flakes heal (2026-11-05)
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
