# TANTRASARA EXPLAINED — production standard (all videos, all chapters)

Locked 2026-11-02, amended by owner call 2026-11-04 (three-layer cards per GOLD-STANDARD, list
engine, persist, IAST-on-cards, 22-chapter set, thumbnail dir). This document
is law for every chapter. Change it only by owner call, same commit as the
code that implements the change.

## 1. The format in one paragraph

Bell and thumbnail open. Granny speaks the title, declares the role, cold
opens. The Sanskrit verse goes up with romanisation and final the moment
chanting starts; a lone chant stays up with its layers through the
following beat. Terms appear in three layers — Devanagari, IAST,
final English — the instant she says them; lists accumulate into one
count-shaped card. Everything else plays over clean white, which returns
at every tone break. No title cards are ever shown. Subtitles carry every
spoken word with karaoke lighting, timed by forced alignment, never by guess.

## 2. Voices (Fish s2.1-pro-free ONLY — free-only law, no paid models ever)

| seat | Fish ID | job | level |
|---|---|---|---|
| granny | `614f8afd83f841048c040b2c6234d2c1` | main narration, titles, demonstrations | reference (-21dB mean) |
| man | `fcfd5ebf496949ed9f76b3a533ee4738` | skeptic objections, dialogue scenes | 75% amplitude of granny |
| verse | `4e873c37d4cb439e9bccc4dc1f633290` | Sanskrit + verses + verse translations | reference |

Key in `~/.config/opencode/.env` (`FISH_API_KEY`), env-only, never in repo,
never printed. Full audition trail: `liked_voices.md` (9 candidates tested).

## 3. Chapter source prep (`cleanup_chapters.py`, `split_chapters.py`)

Canonical set: all 22 chapters, `chapters/chNN.md` (ch06 file is
`ch06-kaladhva.md`). `tantrasara3` (gmail-chrome dump) is IGNORED forever.
Per file, in order: drop jacket-copy blurbs (slang-retelling paragraphs),
drop duplicate H1 titles, `Keep reading`/`Next:` trailers stay spoken where
present (owner ruling pending — ch06 keeps its Next pointer; ch01/02 end on
the body), strip ` <source> +N` citation tails, strip GRETIL `/` `//`
danda markers, drop Devanagari file-level duplication. Rerun is idempotent
(scoped with `--only` so frozen chapters are never touched).

## 4. Storyboard (`build_storyboard.py` + `overrides_chNN.json`)

Blocks: opener, title, verse, narration, dialogue, figure, label, meta,
trailer. Casting rules in fixed order: Devanagari→verse; transliteration
runs→verse; standalone-Sanskrit (every token Sanskrit: diacritic or
lexicon)→verse; quotes with "Abhinav"→man; other quotes→UNCAST (fail
closed); provenance/colophon→meta (never voiced); everything else→granny.
Inline mid-sentence Sanskrit stays with the host block — paragraphs are
never split. Overrides record every judgment call as data (scene
alternation man-first, single-demonstrator stays granny, decomposition
chains stay one voice). Validator: 0 errors 0 warnings or nothing
downstream runs. New chapters: run → fix UNCAST/lexicon → green → frozen.

## 5. Direction (`apply_direction`, same file)

Tags ride Fish free-model brackets, prefixed only, body words never
rewritten (audit proves stripped text == original, allowlist enforced):
verse→`[slowly]`, titles→`[long pause]`, dialogue→`[short pause]`, granny
beats→`[short pause]` only for `BEAT_LEXICON` catchwords and colon-ender
lead-ins. Short sentences are NOT beats. Tag cap 3/sentence.

## 6. Glossary (`glossary_chNN.json` + T1 literals)

Term cards need three layers (owner call 2026-11-04 — literal morphemes
parked proposed, never on screen): citation Devanagari (never rebuilt from
the folded key — M15) + IAST romanised in lightest grey + final English in
darkest grey. Glosses drafted from the author's own surroundings, every one
`proposed` until the owner confirms in bulk — video shows confirmed terms
only. Unconfirmed terms play over white — never on cards. Keys are folded ASCII (diacritics
stripped, lowercase). Owner confirms in bulk; engineer flips status, never
edits glosses silently.

## 7. Holds and cards (`holds.py` — single source for sheets AND video)

Types: thumbnail opener (`assets/thumbnail/chNN.png`, ch01 rainbow emblem
law, fits above subtitle zone, never fullscreen-bleed), verse (Devanagari
+ IAST, wrapped to fit, auto-fit floor, assert no overflow), term (three
layers, centered under the Sanskrit), list (count
decides the shape: 1 centered, 2 side by side, 3 row-or-triangle, 4
corners, 5 corners + middle, window slides past five), title, figure.
Lone glossed chants persist with layers through the following block; cues
win over persist. White is the default hold; cards interrupt at cues;
white returns
at section breaks, long-pause beats, dialogue entries. Every card asserts
stack clears subtitle zone and frame edges — collisions fail the render.
Subtitles: FE 46→40, y=860 safe zone, max 2 lines, ink lit / grey unlit.

## 8. Audio (`render_chapter.py`, free Fish)

Group consecutive same-voice blocks per section into single TTS calls
(prosody over beats). Filenames carry `sha1(voice|directed-text)` —
re-runs only render changed groups, everything else is a cache hit.
Receipts log every call (chars, hash, duration). Track chars per chapter
against the free tier. Voice audio -21dB mean.

## 9. Alignment (`align_group.js`, MMS forced align — same engine as chant)

en-IN adapter for English, sa-IN for Sanskrit. Diacritics folded and
numbers spelled for the aligner ONLY (display text untouched, 1:1 mapping
asserted). Quality bar: mean ≥0.85, zero non-monotonic. Boundaries at word
onsets; gaps belong to the prior word. Never distribute time
proportionally. MMS deps live in `/tmp/mssmod` (reinstallable, excluded
from disk budgets).

## 10. Assembly (`assemble_chapter.py`)

Bell (ding, +6dB, peak checked under 0dB) opens; 0.4s beds between groups,
1.0s between sections. Groups resolved by content hash, never by stale
block IDs. Duration asserted against sum of parts.

## 11. Video (`build_clip.py`)

Thumbnail from frame 0 through the intro (first tone break); verse cards
while chanting; term/title/figure cards at cues; clean white otherwise. Subtitles:
IAST transliteration for verse blocks (Devanagari has no glyphs in the
subtitle face — bare boxes otherwise), verbatim otherwise. 30fps,
libx264, AAC. Frames verified by eye before upload (tofu, overflow,
collisions, timing).

## 12. QA gates (in order, every clip)

1. Validator green (storyboard). 2. Machine checks (durations add up,
   no empty audio, bounds asserts passed at render). 3. Self-review:
   frames pulled and read at chant start, mid-verse, narration, dialogue
   turns. 4. Whisper head-check (words present, not timing). 5. Qwen omni
   for taste ONLY — timing/identity claims require transcript or waveform
   corroboration; timestamps beyond file length void the pass. 6. Owner
   ears dispose. Model verdicts never gate alone.

## 13. Delivery (R2 `svread-audio/tantrasara/`, public)

`chNN_openingN.mp4` for clips, `holds_chNN/` for sheets, `voices/` for
auditions. `rclone copyto` for exact keys (`copy` to a filename creates a
directory — known footgun). Verify with HEAD (200 + byte match) after
every upload. Overwrites are fine; CDN settles in minutes.

## 14. Storage (local disk is 98% full — this is load-bearing)

- Renders write straight to the opencode2 volume mount (`~/vol`), never
  local disk. R2 holds shipped copies + the MMS deps tarball
  (`tantrasara/tools/mmsmod.tgz`, restore: download + untar to /tmp).
- `run_all` opens with a storage preflight (local >=1G, volume >=4G free,
  fail loud) and closes with transient cleanup (frames, f32, tmp mp3s).
  Model caches (whisper, MMS onnx, browsers, npm) belong to other lanes —
  never delete them.
- Series footprint ≈ 8h audio ≈ 2.5GB wavs + 1GB mp3s on volume (11G free).
  Frames are transient (deleted per chapter after mux).
- Never `rclone copy file remote/path/file` (creates a directory) — use
  `copyto` for exact keys, verify with HEAD. Never trust mount reads
  blindly — retry or copy down on failure.

## 15. Git (repo `prx0r/tantrasara`, public)

Commit: chapters, scripts, storyboards, overrides, glossaries, sheets,
docs. Never commit: audio, frames, model caches, keys, R2 credentials.
Render outputs live on the opencode2 volume (`~/vol`), never local disk
(98% full — renders write straight to the mount). One concern per
commit, push same day.

## 15. Per-chapter checklist (in order, no skipping)

1. Split + clean source → 2. storyboard green → 3. casting sheet →
   owner marks → 4. overrides in, green again → 5. glossary draft →
   6. holds timeline → 7. owner confirms glossary → 8. render audio →
   9. MMS align (check means) → 10. assemble → 11. holds sheets, owner
   eye → 12. video → 13. self-review frames → 14. Qwen taste →
   15. upload + verify → 16. owner ears → 17. commit + push.

## 16. Standing owner calls (decided once, recorded here)

- IAST on term and verse cards as a light-grey second line; full IAST
  transliteration blocks live in subtitles only.
- All Sanskrit one standard Deva size (84); only assignment moves.
- No title cards shown in video (spoken titles stay).
- Lone glossed chants persist through the following block.
- Thumbnail holds from frame 0 through the intro (per-chapter art).
- Man at 75%. Bell ding +6dB. Free Fish only, always.
- Unconfirmed glosses never render. UNCAST never defaults.
