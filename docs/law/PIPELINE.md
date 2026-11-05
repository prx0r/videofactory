# PIPELINE — the complete operating manual (2026-11-04)

One chain, two lanes, zero decisions at render time. This is the document
an agent reads to run the whole factory. Law lives in STANDARD.md and
GATES.md; this explains it. RUNTIME.md is the gospel; PROCESS.md is the
canonical chain summary.

## 0. Mental model (30 seconds)

Markdown chapters go in. Frozen storyboards assign every paragraph a voice.
Voice groups become cached audio. Word-onset alignment times every word.
Cards computed from the same data burn onto frames. The mp4 falls out —
then gates prove it. Publish is a view of the storyboard, approval pins
SHAs, golden diffs the future. Anything that changes the picture changes
the storyboard first.

## 1. Readings map (what to read for each job)

- New here → RUNTIME.md, then this file, then GATES.md.
- Rendering a chapter → STANDARD.md §4–§11 + VISUAL.md + approved file.
- New chapter intake → split script + BUILD-NOTES intake entries +
  `shiva/SHIVA-INTAKE.md` for the lane pattern.
- Something looks wrong → HANDOVER.md traps + MISTAKES.md + PROCESS_NOTES.md
  wrong-vs-right sections.
- Casting call → skill tantrasara-storyboard (rules + unsure list) +
  casting sheets; cards questions → skill tantrasara-holds.
- Translation data → LAYERS.md (T1→L4 + card layers, per-chapter status).
- Where is everything → REGISTRY.json (live) + CHAPTER_PREP.md (rundown).

## 2. Stages in depth

### 2.1 Source (`chapters/`, `shiva/chapters/`)

Chapter files are slang retellings with H1 title, `##` sections, Devanagari
verses, IAST lines, `Literal:` glosses, dialogue in quotes, provenance
tails. Splitters (`split_chapters.py`, `shiva/split_shiva.py`) cut dumps
into per-unit files and strip only machine debris (gmail headers,
citation tails, trailers, part labels, repeated formulae) — never prose.
Headings are consumed in document order (shiva: sutra order, asserted);
post-boundary material attaches forward; appendices stay reference except
explicit colophons. Reruns must be idempotent over cleaned files
(`--only` scoping; M13).

### 2.2 Blocks (`build_storyboard.py`)

Every paragraph becomes one block `{id, section, type, voice, text,
directed}` — paragraphs are never split, so inline Sanskrit stays with
its host. Casting order is fixed: opener bell → image/provenance to meta
→ trailers to granny → labels to none → numeric/ALLCAPS to figure (with
the shouted-punchline guard: multi-word period sentences without
digits/dashes/slashes stay spoken — M-edge-8) → Devanagari-letter to
verse → Abhinav quotes to man → other quotes UNCAST (fail closed) →
standalone Sanskrit (every token diacritic/lexicon, ≤6 words) to verse →
everything else granny. Per-bid voice forcing in overrides (owner calls,
e.g. chapter-name lines to granny so her intro runs unbroken; verse-type
forced off-seat retypes to narration; unknown bids fail closed).
Direction prefixes Fish tags from an allowlist; audit proves the body
untouched; tag cap 3. Gate: 0 errors, 0 warnings. Totals recorded
(words per voice, 150wpm estimates).

### 2.3 Glossary (`glossary_chNN.json`)

Citation Deva + IAST (derived) + T1 literal (square brackets) + final
gloss per term, each `proposed` until bulk-confirmed. Video shows
confirmed gloss, and the literal only on its own confirmed status; sheets
show proposed for review. Folded-ASCII keys are lookup-only — display
text never comes from a key (M15). Unconfirmed terms play over white.

### 2.4 Publish and approve (`publish_review.py`, lane variants)

Asserts green, writes readable storyboard + holds timeline + contact
sheets, uploads to R2 (`review/chNN/`), records `manifest.json`
(`approved: false`, storyboard + glossary SHAs). Owner blesses by
message; engineer records `approved_chNN.json` pinning SHAs. Render
refuses without it and rechecks SHAs. Never self-granted.

### 2.5 Audio (`render_chapter.py`, Fish s2.1-pro-free ONLY)

Consecutive same-section same-voice blocks merge into one TTS call
(prosody over beats). Filenames carry `sha1(voice|directed-text)` —
re-runs are cache hits; receipts log every call. `--dry-run` plans,
`--limit` caps, `--force` re-renders. Free-tier law: dry-run must print
~$0.00 and the model string must read `-free`. Voice −21dB mean, man 75%.
Singleton sounded phonemes take human clips (same hash path). Before
any chapter render, `probe_rough.py` voices the mangle-prone blocks:
English round-trips by whisper, Sanskrit + punctuation to owner ears.

### 2.6 Align (`align_group.js`, MMS forced align)

en-IN narration, sa-IN Sanskrit; folding plus number spelling for the
aligner ONLY, display untouched, 1:1 mapping asserted. Bar: mean ≥0.85,
zero non-monotonic. sa-IN takes Devanagari (its romanizer rejects IAST);
en-IN takes folded ASCII — Devanagari tokens folded to IAST for the
aligner (granny speaking inline Sanskrit, proven 0.946). Gaps belong to
the prior word; time is measured, never distributed.

### 2.7 Holds and cards (`holds.py`, single source for sheets AND video)

Thumbnail intro bug (`intro_hold`, shared): per-chapter art, ch02+
numeral + canonical title (Deva 84, layers centered under the Sanskrit,
mandala clearance measured from the art). Verse cards bare Devanagari
(subtitles carry the romanised); lone glossed chants keep all four term
layers and persist one following block. Terms: Deva + IAST + literal +
final, grey ramp down. Lists: count decides the shape (1 centered, 2 side
by side, 3 row-or-triangle, 4 corners, 5 corners + middle, window slides
past five). White is the default hold and a dramatic device — cards
interrupt, white returns at breaks. Every card asserts subtitle zone,
frame edges, pairwise overlap, column width.

### 2.8 Video (`build_clip.py`)

Bell +6dB opens; deterministic beds (0.8 structural/dialogue/section,
CRISP 2.8 after multi-line chants — linger then boom white — 0.6 verse
singles, 0.3 flow; 2.8 not 3.0: the dead-air tripwire fires past 3.0s).
Mixed-script lines split first (author's roman half IS the IAST line;
Deva blanks in subtitles with karaoke remapped to visible words).
Subtitles never carry Devanagari glyphs (tofu — M3, all voices). One
frame per word at onsets. Prints COVERAGE (fails >85% white past 60s).
Writes `render_meta.json` (cuts, duration, coverage, cues, bids) plus a
word-level `.subs.json` for the gate.

### 2.9 Verify, golden, delivery

`verify_clip.py`: geometry, levels, 3s silence ceiling, whisper word
coverage, motion. `golden.py`: seal after owner ears; check fails on
duration ±2s, cue reorder/miss/drift ±3s, white ±5pp, cuts drift.
`rclone copyto` exact keys, HEAD 200 + byte match. Storage: renders to
the volume mount, never local; preflight local ≥1G volume ≥4G; transient
frames cleaned. Git: chapters, scripts, storyboards, overrides,
glossaries, sheets, docs — never audio, frames, caches, keys.

## 3. Lanes

| | tantrasara | shiva |
|---|---|---|
| units | 22 chapters | s00 intro + 77 sutras |
| source | ranged dumps | `shivasutrasfinal` gmail dump |
| storyboards | `storyboard_chNN.json` | `shiva/storyboards/storyboard_sNN.json` |
| text | slang exposition | slang exposition, sūtra-anchored |
| voices/cards/gates | the law | identical (shared builders) |
| lane files | — | split/casting/glossary/publish/runner + intake log |
| art | rainbow emblem (ch01) | line-art Shiva series mark (small) |
| open | approvals, confirms, disk | casting bless, confirms, art numerals, render paths |

Lane routing (`holds.lane_for`) keeps builders single-copy: glossaries,
thumbnail dirs, numeral semantics resolve per storyboard path.

## 4. Running the line

`REGISTRY.json` is the live board (stages, locks, queue).
`run_queue.py` picks next work; `watch.py --register/--check` tracks
background jobs (never sleep-block: nohup + log + poll). One video build
at a time (lock — fixed `/tmp` paths). `sysload.sh` gates prep
parallelism. Long batches run overnight under nohup; one chapter failing
never blocks others.

## 5. When output looks wrong

Rebuild from the storyboard, never trust a stale mp4. Green? SHAs match?
Tofu scan (no Deva in subtitle face, any path)? Holds from the shared
source? Timings (MMS means, folding)? Deva citation correct (M15)?
Qwen taste-only with transcript corroboration. Frame reads at every hold
change. Log findings (M-class), fix data or code same-commit, re-prove.
