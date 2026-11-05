# PROCESS — the one chain (canonical, 2026-11-04)

Storyboard is the render. Publish is a view of the same file. Assembly
resolves the same hashes. Video burns the same onsets. Anything that
changes the picture changes the storyboard first. BUILD-NOTES remains the
log and wins on conflict. STANDARD remains law until amended same commit
as code.

## 0. Source

`chapters/chNN.md`, ch06 file is `ch06-kaladhva.md`. Split then cleanup,
idempotent, scoped with `--only` so frozen chapters are never touched.
M13 blanks append first, diff stat after every run. Provenance and
attachment lines route to meta none. URLs and witness labels route to meta.
Devanagari letter voices a block, digits never do. Trailers: Next lines
stay spoken where present, see open delta below.

## 1. Blocks

`python3 build_storyboard.py <chapter.md> <storyboard.json> [overrides]`
Paragraphs never split. Fixed order: opener bell, image and provenance to
meta, Next to trailer granny, labels to none, number headings and short
ALLCAPS to figure none, Devanagari letter to verse verse, Abhinav quotes
to man, other quotes to UNCAST and fail closed, standalone Sanskrit to
verse verse, everything else to granny. Overrides map bid to man or granny
for UNCAST only, remapped by text identity when text moves, never
hand-edited. Direction prefixes only from the allowlist, audit proves the
body untouched, cap 3 per sentence. Gate 0 errors 0 warnings. Output block
`{id, section, type, voice, text, directed}` plus `words_per_voice` and
150wpm estimates. Types opener title verse narration dialogue figure label
meta trailer. Voices granny man at 75 percent verse none.

## 2. Intro

Opener plus b1 through handoff. ch01 adds role declaration, 110 words to
handoff. ch02-22 share spoken number granny, chanted Sanskrit name verse at
b2, English tagline granny, Right then beat, Last chapter recap. Budget 150
words verse excluded, recap 5 beats, no repeated greeting. ch06 and ch14
flagged for trim or exception. Visual thumbnail from frame 0. b2 verse card
is the amendable slot: flip to granny in overrides to hold thumbnail
through the name. Thumbnails live in `assets/thumbnail/chNN.png`, ch01
rainbow emblem, fallback to legacy `assets/thumb_ch1.png`.

## 3. Glossary and holds

`glossary_chNN.json` holds Deva plus gloss, every entry proposed until the
owner confirms. Only confirmed terms render cards, proposed plays over
white by design. Term card is full compound plus one gloss line, no
splitting, no romanisation on cards. Holds computed in `holds.py`, single
source for sheets and video: thumbnail to first chant, verse Devanagari
only max 3 pairs, term on cue clamped at next cue so newer wins, white at
every tone break section break long-pause beat and dialogue entry. Target
20 percent white, fail over 85 percent past 60s. Subtitles verbatim except
verse in IAST. Cards assert clear of subtitle zone y 860 and frame edges.

## 4. Publish and approve

`python3 publish_review.py <ch>` asserts green, writes readable storyboard
plus timeline plus contact sheets, uploads to R2 `review/chNN`, writes
local manifest with storyboard and glossary SHAs approved false. Owner
blesses by message, engineer records `approved_chNN.json` pinning SHAs.
`run_all` stage render refuses without it and rechecks SHAs. No approval,
no tokens.

## 5. Audio and assembly

`render_chapter.py` groups consecutive same-voice same-section blocks, one
Fish s2.1-pro-free call each, filename carries sha1 of voice plus directed
text, receipts map bids to files with chars hash duration. Voice minus 21dB
mean. Singleton sounded phonemes take human clips (same hash path).
Before rendering: `probe_rough.py` voices the mangle-prone blocks;
English round-trips by whisper, Sanskrit and punctuation by owner
ears — nothing renders until suspects are heard. Assembly bell ding plus 6dB opens, beds deterministic from the clip
rhythm table: 0.8 structural dialogue section-end and long-pause, 0.6
verse, 0.3 flow. Duration asserted against sum of parts. Missing groups
block loudly. Tuning pauses is re-assemble and re-mux, never re-render.

## 6. Video verify golden delivery

`build_clip.py` aligns each group with MMS, en-IN narration sa-IN chant,
folding plus number spelling for the aligner only, 1:1 map asserted, mean
0.85 minimum, boundaries at word onsets with gaps to the prior word. One
frame per word, karaoke ink lit grey unlit, coverage printed, meta JSON
with cuts duration coverage cues beside the mp4. `verify_clip.py` proves
geometry audio levels silence coverage motion. Taste is Qwen only with
transcript corroboration. Owner ears dispose, then `golden.py seal`,
tolerances duration 2s cue reorder or miss cue drift 3s white 5 points.
Delivery `rclone copyto` exact keys, HEAD 200 plus byte match. Storage
writes to the volume mount never local disk, preflight local 1G volume 4G,
transient frames cleaned. Git commits chapters scripts storyboards
overrides glossaries sheets docs, never audio frames caches keys.

## Open deltas to fold into law (2026-11-04 refresh)

- DONE: duplicate extensionless storyboards deleted; `assets/thumbnail/`
  canonical with ch01 rainbow (rest fall back to legacy art — wrong art,
  flagged below); STANDARD §3 now names all 22.
- STILL OPEN: beds in `assemble_chapter.py` read 0.4/1.0 vs clip rhythm
  table above (mp3 mixes vs video mixes diverge). Next/Keep reading kept
  versus stripped needs one owner line. Dialogue with verse voice in ch04
  and ch13 needs a name or reclassify. Thumbnails ch02–22 missing (fallback
  shows ch01 art). Every term mention fires its own cue at its word
  onset (proven: b37 fires x3 — the old "one cue per block" note was
  wrong). `verse_gloss_chNN.json` (T1 literal + L3 final per
  chant, `mine_verse_gloss.py`) parked proposed after a same-day revert —
  verses render Deva + IAST until re-blessed. `review/` packs versus
  `reviews/` frozen listener reviews need distinct names in the tree.
