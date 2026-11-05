# PROCESS NOTES — how chapter audio/video gets built and proven

Locked 2026-11-04. Each step's output is the next step's input; nothing is
estimated, nothing is decided at render time. Storyboard is the render.

## The chain (each step's output is the next step's input, nothing estimated)

1. **Storyboard** (`build_storyboard.py`): markdown → blocks with voice +
   direction tags. Gate: 0 errors 0 warnings. Overrides are positional —
   if chapter text moves, remap by quote text, never reuse stale IDs.
   Overrides map bid → voice; quote UNCASTs fail closed without one.
2. **Render** (`render_chapter.py`): consecutive same-voice blocks per
   section merge into one Fish call (`s2.1-pro-free`). Filename carries
   `sha1(voice|directed-text)` — re-runs only render changed groups.
   Receipt per call (chars, hash, ffprobe duration) in
   `renders/<ch>/receipts/calls.jsonl`. `--dry-run` plans, `--limit N`
   caps, `--force` re-renders. Voice -21dB mean, man at 75%.
3. **Assemble** (`assemble_chapter.py`): bell (ding, +6dB, peak checked
   under 0dB) + groups with rhythm beds. Groups resolved BY CONTENT HASH,
   never by stale block IDs. Duration asserted against sum of parts.
   NOTE: assemble beds still read 0.4 in-flow / 1.0 at section ends while
   the video build uses 0.8 structural / 0.6 verse / 0.3 flow — mp3 mixes
   and video audio diverge; canonical is the clip table (open delta).
4. **Holds** (`render_holds.py` → `holds.py`, single source for sheets AND
   video): thumbnail intro bug (`intro_hold`: ch01 clean, ch02+ numeral
   top-right in FE 150) / verse (Deva + IAST, M4 split) / term (four
   layers: Deva citation form + IAST + T1 literal + final gloss, grey ramp
   down, brackets not parens) / list (count decides the shape, window of
   five   slides) / verse persist (every verse hold stays one following block
  as standard, owner call 2026-11-04) /
   title / figure / white (the default hold, used as dramatic effect —
   never filler). Every card asserts subtitle zone, frame edges, pairwise
   non-overlap, column width — collisions fail loud.
5. **Align** (`align_group.js`, MMS forced align — same engine as the
   chant pipeline): en-IN narration, sa-IN Sanskrit. Diacritics folded
   and numbers spelled FOR THE ALIGNER ONLY (1:1 mapping asserted).
   Bar: mean ≥0.85, zero non-monotonic. sa-IN takes raw Devanagari;
   en-IN takes folded ASCII (its romanizer rejects IAST diacritics and
   bare digits — both handled in `spoken()`). Granny reading Devanagari
   script is UNPROVEN for MMS en-IN — probe before batching (ch02 b2).
6. **Video** (`build_clip.py`): one frame per word, boundaries AT word
   onsets (gaps belong to the prior word — never distribute time
   proportionally). Mixed-script lines split first (M4 `split_scripts`,
   promoted from the pilot builder to shared law): the author's own roman
   half IS the IAST line, the Deva blanks in subtitles (karaoke indices
   remap to visible words). Thumbnail intro bug to first chant; verse
   cards while chanting; term/list cards at confirmed-gloss cues (clamped,
   runs accumulate); persist spans; clean white otherwise. Prints
   COVERAGE, fails >85% white past 60s. Writes `render_meta.json` with
   cuts, duration, coverage, cues beside the mp4.
7. **Verify** (`verify_clip.py`, post-render gate, runs after every
   video): streams 1920x1080 + audio present; levels in band
   (mean -32..-12dB, peak >-8dB); no silence over 3.0s anywhere;
   ordered-subsequence whisper match over every narration block
   (exact-match failed on whisper variants — subsequence with 0.35
   floor, verse excluded); 70%+ frame variance (not frozen). Report
   JSON beside the clip; FAIL stops the line before review-pack.

## How timings are confirmed (no trust, only checks)

- **MMS scores**: mean + min + nonmono printed per group; anything under
  bar stops the line for that group (not the chapter).
- **Duration math**: assembly total == bell + Σ groups + Σ beds, verified
  by ffprobe. A mismatch means a wrong file got in — investigate, never
  adjust a constant to make it fit.
- **Whisper head-check**: transcribe the mix head; the words must be
  there in order. Whisper is a CONTENT check only (words present), never
  a timing authority — short clips and Sanskrit garble it.
- **Frame reads**: pull frames at every section boundary (hold changes)
  plus 2–3 mid-section karaoke states and READ them: right card, right
  subtitle, no overflow, no tofu, highlight on the spoken word.
- **Qwen omni**: taste and flow ONLY. Timing/identity claims need
  transcript-or-waveform corroboration. Timestamps past file length void
  the pass. Single passes are hints; corroborated structure is evidence.
- **Owner ears dispose.** Everything above is just the ticket to get heard.

## List engine + four layers (2026-11-04) — wrong vs right

Locked look: count decides the shape, one standard Deva 84 everywhere;
every layer centered under the Sanskrit; literal morphemes in square
brackets. Reference PNGs: `review/ch01/conveyor_std.png`,
`review/ch01/layers_centered.png`, `review/ch01/layers_single2.png`.

WRONG, each proven by a render before the fix:
- Term cues flashing one by one. A 127s samsara span swallowed the diksa
  cue (M11); rapid cues superseded after 3–5s so no list ever stood whole.
  RIGHT: runs of 2+ cues with no event gap accumulate into one
  count-shaped card (1 centered, 2 side by side, 3 row-or-triangle, 4
  corners, 5 corners + middle); the window slides past five.
- Verse cards in video with no gloss. Sheets passed glossary into
  `render_hold`, `build_clip` passed None, so chants like Svātantrya
  showed bare Deva while sheets showed Deva + gloss. RIGHT: confirmed
  glossary flows into verse holds in video too.
- Single-word chants clearing instantly. "Aṇu." vanished the moment granny
  said "That's you." RIGHT: lone glossed chants persist with all layers
  through the directly following block; cues win over persist.
- Folded keys rebuilt wrong Devanagari (M15): folded `cit-sakti` back through
  the transliterator gives चित्-सक्ति (स for श). RIGHT: cards always use
  the glossary citation Deva (चित्शक्तिः); keys are lookup-only.
- Corner stack at invented small type (Deva 44) under a big middle (84),
  tight 30px gulps then a 280px dead drop to subtitles. RIGHT: all slots
  house standard 84; only assignment moves.
- Seven-member stacks overflowing the subtitle zone (measured 1306 vs 860).
  RIGHT: window of five max, longer lists slide; subtitle-zone, pairwise
  non-overlap and column-width asserts fail the build instead of shipping.
- Whole-chant T1 literal + L3 final on verse cards (mined for all 22 via
  `mine_verse_gloss.py`, matches scored) — reverted same day, owner call.
  Verses stay Deva + IAST; terms keep all four layers. Miner output parked
  in `verse_gloss_chNN.json` (proposed) for a future revisit.
- Mixed-script duplication (ch02 b2 caught live 2026-11-04): a
  Deva-plus-roman line rendered the roman half twice — big in the Deva
  face and again small as IAST, same in subtitles. RIGHT: `split_scripts`
  promoted to shared law; author's roman half IS the IAST line,
  transliteration only where no roman exists; subtitle Deva words blank
  when the roman duplicates them, karaoke remapped to visible words.

## ch02 intro (2026-11-04) — her show, still open

Thumbnail treatment mirrors ch01 with a 02 top-right (`intro_hold`,
shared by sheets and video; ch01 blessed reference untouched). Open
owner call from the first proof render: the name-chant (b2) fires ~4s
in, before any of her intro patter — it should be her intro. Probe
rendered (`review/granny_probe_b2.wav`, 4.2s, granny reading b2
verbatim); whisper garbles Sanskrit so transcript proves nothing — owner
ears dispose. Options: (A) flip b2 to granny by override — title, name,
tagline, recap all hers over thumbnail+02, first verse card at first
body chant (needs builder support for per-bid voice forcing + MMS
en-IN Deva-token probe); (B) keep the chanted name-anchor. Render gate
still closed anyway (no approvals); first-minute render queued behind
this call plus local disk (0.5G vs 1G preflight).

## Failure log (ch01 full run, 2026-11-02)

- ch01 full chapter: 111 blocks, 7m19s, 15MB. Render 9/9 groups, MMS means
  0.92–0.96 across groups, assembly == sum of parts, frames verified at
  opener/verse/term/narration checkpoints, whisper head-check clean.
- Lesson: `rclone copy <file> <remote-dir>/<filename>` creates a directory
  named like the file — always `copyto` for exact keys, verify with HEAD.
- Lesson: the rclone sftp mount flakes on reads under load ("Impossible to
  open") — single `cp` retries or `rclone copy` down, never assume.
- Lesson: Fish TTS on Devanagari returns short garbage-free clips, but MMS
  sa-IN needs Devanagari tokens (its romanizer rejects IAST diacritics and
  bare digits) — fold + spell numbers for the aligner only.
- Lesson: subtitle face (Cormorant) has no Devanagari glyphs — verse
  subtitles render in IAST transliteration, never Devanagari.
- Lesson: verse subtitles in an earlier cut showed the wrong block's text
  because the clip range split a rendered group — clip ranges must align
  to group boundaries (builder asserts).

## The crisp moment (2026-11-04) — why this is gorgeous
A chant is sound becoming meaning. The card holds the bare syllables while
the voice fills them; when the voice stops, the meaning hangs in the air
for almost three seconds of held silence — the eye re-reads what the ear
just received — and then clean white, and her next line lands like a
verdict. Nothing moves, nothing decorates, nothing explains. Restraint is
the whole aesthetic: one idea per frame, ink on white, silence as
punctuation, white as the exhale. It works because every layer was already
proven separately (bare Deva cards, word-onset timing, deterministic beds)
so the moment is pure composition, not effects. New pockets to hunt: term
stacks held a beat past the last cue before clearing; dialogue entries
preceded by half a breath of white; section ends exhaled the same way.
Each pocket is a bed constant plus a frame proof — never a guess.
