# BLOCKS — text to blocks to full-chapter mp4

Locked 2026-11-04. A chapter is blocks. The renderer never decides, it only
resolves blocks to cached audio and concatenates.

## 1. Text to blocks (`build_storyboard.py`)

Input: `chapters/chNN.md`. Output: `storyboard_chNN.json`.

- Split on blank lines into paragraphs. `##` lines become sections. First
  `#` line is the chapter title. Everything else keeps its paragraph shape —
  paragraphs are never split, so inline Sanskrit stays with its host block.
- Classify in fixed order: opener bell, image/provenance to meta none,
  `Next:` to trailer granny, `ORIGINAL SANSKRIT` / `TRANSLITERATION` labels to
  none, `# <number>` and short ALLCAPS to figure none, Devanagari LETTER to
  verse verse, quote-led to dialogue man if it names Abhinav else UNCAST,
  standalone-Sanskrit (every token diacritic or lexicon, max 6 words) to verse
  verse, everything else to narration granny.
- Overrides: `overrides_chNN.json` maps `bID -> man|granny` for UNCAST quotes
  only. Scene alternation is man-first by convention. Every call is data.
- Direction: `apply_direction` prefixes `[slowly]` verse, `[long pause]`
  titles, `[short pause]` dialogue and granny beats (BEAT_LEXICON catchwords
  plus colon-enders only). `audit_direction` proves stripped directed text
  equals the original, allowlist enforced. Tag cap 3 per sentence.
- Validate: 0 errors 0 warnings or nothing downstream runs. UNCAST is an
  error, never a default. Verse on non-Sanskrit and non-quote dialogue are
  warnings. Totals recorded: `words_per_voice` plus `est_min` at 150wpm.

Block schema: `{id, section, type, voice, text, directed}`. Types: opener,
title, verse, narration, dialogue, figure, label, meta, trailer. Voices:
granny `614f…`, man `fcfd…` at 75%, verse `4e87…`, none visual-only.

Intro is conventional, not a separate type: `b_opener` bell, `b1` title
granny, overview narration granny through the handoff line, first verse
chant. Chapters 02-22 share bell, spoken number, chanted Sanskrit name,
English tagline, `Right then`, recap. Chapter 01 adds the role declaration.

## 2. Blocks to audio (`render_chapter.py`)

Grouping: consecutive blocks, same section, same voice, one Fish call.
Voice none skipped. Opener is an asset copy, never rendered.
Singleton verse blocks sounding one mapped phoneme take the human
clip instead of Fish (owner call; same content-hash path, receipts
carry src/gain, -21dB mean, -1dB peak ceiling).

Before the chapter render: rough probes (`probe_rough.py`) voice
the Fish-mangle-prone blocks cheaply — whisper round-trips English,
Sanskrit-dominant and punctuation-heavy blocks go to owner ears and
Qwen with their wav clips. Nothing renders until suspects are heard.

Filename carries the link: `groups/<sec-slug>/gNNN_<voice>_<sha1>.wav`
where sha is `sha1(voice|directed-text)` first 12 hex. Re-runs with unchanged
text are cache hits. `--dry-run` prints plan plus chars, `--force`
re-renders, `--limit N` caps calls. Every call appends to
`renders/<ch>/receipts/calls.jsonl` with file, voice, chars, bids, sha,
duration. Voice audio -21dB mean, man attenuated.

## 3. Audio to full chapter (trivial by construction)

- `assemble_chapter.py <storyboard> <out.mp3>`: rebuilds groups with the
  same same-section same-voice rule, resolves each by content hash via
  `calls.jsonl` bid map plus glob on hash, never by stale bid. Bell ding
  +6dB opens. Beds 0.4s in flow, 1.0s at section ends. Asserts duration
  against sum of parts. Missing groups block loudly.
- `build_clip.py <storyboard> <bids> <out.mp4>`: same groups, MMS forced
  align per group (en-IN narration, sa-IN chant, folding plus number spelling
  for the aligner only, 1:1 word map asserted, mean 0.85 minimum). Flat word
  timeline with absolute onsets, beds included. Holds from `holds.py`:
  thumbnail to first chant, verse cards (Deva + IAST) while chanting, term
  cards in four layers on confirmed glossary cues, list runs accumulated by
  the count engine, single-word chants persisting one block, white
  otherwise. Subtitles verbatim except verse in IAST. Beds 0.8 titles
  dialogue section ends and long-pause beats, 0.6 verse, 0.3 flow (clip
  rhythm is canonical; `assemble_chapter.py` mp3 beds still read 0.4/1.0 —
  open delta). Prints COVERAGE, fails
  over 85 percent white past 60s. Writes `render_meta.json` with cuts,
  duration, coverage, cues.
- Full chapter is the degenerate case: bids equals every block except
  `b_opener`. No special path. Segment renders and the full render resolve
  the same hashes, so tuning a pause is re-assemble and re-mux, never a
  voice re-render.

## 4. Prove it (`verify_clip.py`, `golden.py`, `run_all.py`)

Verify checks geometry 1920x1080 30fps plus audio, levels in band, no uncomposed
silence over 10s, every narration and dialogue head plus tail heard in order by
whisper, motion so frozen video fails. Golden seals duration cuts coverage
and cue sequence on owner ears pass, check fails on duration drift 2s, cue
reorder or miss, cue drift 3s, white drift 5 points, cuts drift. `run_all.py`
drives preflight, board, cast-check, publish, render gated on
`approved_chNN.json` SHAs, assemble, holds, video, verify, golden-check,
review-pack, cleanup. One chapter failing never blocks others.
