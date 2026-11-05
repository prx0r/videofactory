# PLAYBOOK — zero to shipped chapter (canonical, 2026-11-04)

The one executable document. Every step states its gate; a red gate
stops the line, never the run. Laws live in STANDARD/GATES/VISUAL;
this file only sequences them. How to use the other notes is at
the bottom.

## 0. Read (10 minutes, once)

START-HERE.md → PROCESS-NOTES2.md → IMPACT-FLOW.md → this file.
Then work. RUNTIME.md is gospel; GATES.md is binary law.

## 0b. Preflight (every batch, no exceptions)

`preflight.py [--chapters ..]` — disk, lock, approval SHAs, V5,
audio cache, keys, models. RED stops everything before a token
burns. This is the impossible-to-fuck-up guard.

## 1. Storyboard (no audio, no video)

1. `build_storyboard.py <chapter.md> <storyboard.json> [overrides]`
   → green 0 errors 0 warnings or stop. Paragraphs never split.
   UNCAST never defaults. Overrides remapped by text identity
   (M12), never hand-edited (M18).
2. `gate_storyboard.py <storyboard.json>` → GREEN or stop. Checks:
   green sheet, drops exist + group-final (M6) + justified,
   intro thumbnail ≤60s, H8 rhythm advisory (reported, never
   fails alone), folded keys, confirmed terms carry citation
   Deva (M15), literals square brackets.
3. `render_holds.py` → read EVERY hold PNG against GATES eye
   lines → file `review/chNN/storyboard_proof.md` (good/bad per
   frame) → fix → re-proof to green.
4. `publish_review.py <ch>` → R2 pack + manifest.

## 2. Voice (cheap probes before expensive renders)

5. `probe_rough.py <storyboard> <outdir>` → Fish-mangle-prone
   blocks voiced cheaply. Whisper round-trips English only;
   Sanskrit-dominant + punctuation-heavy go to owner ears with
   wav clips (whisper garbles short Sanskrit by design).
   Nothing renders until suspects are heard.
6. `render_chapter.py <storyboard>` (Fish free ONLY, dry-run
   must read ~$0.00 + `-free`). Singleton sounded phonemes
   take human clips (same hash path, receipts src/gain,
   -21dB/-1dB ceiling). Groups are content-hash cached —
   re-runs are hits. Missing groups block loudly.

## 3. Video (one build at a time, staged audio, chunked align)

7. `run_blocks.py <storyboard> <outdir> [600]` → group-aligned
   mp4 parts + concat list. Audio staged locally with retries
   (mount flakes kill node silently). Align >300 words splits
   on measured silence with offset stitch (proven 0.921).
   Drops scoped per range; subtitle wrap 46→40→36→32 with bid
   in the assert; thumbnail holds the intro only; verse cards
   persist one following block as standard.
8. `prove_clip.py <storyboard> <part.mp4> <outdir>` per part →
   boundary frames + mids + gate run. READ every frame vs the
   storyboard beats → notes → fix → re-proof. Red stops.
9. Concat proven parts → `verify_clip.py` (geometry, levels,
   10s-silence, whisper coverage with slice-check on miss,
   motion) → `check_voices.py` (every seat audible — M29) →
   `golden.py check` → `publish_review.py`.

## 4. Ship (exact keys, verified)

10. `rclone copyto` (never `copy` — M7) → HEAD 200 + byte match
    → owner ears → `golden.py seal` → commit one concern + push.
    R2 gets review packs + sealed videos only. No stale root
    keys (M1/M27): one canonical name per deliverable.

## 5. Blessings (bounded delegation, owner: u bless them urself)

I bless: approvals (SHA-verified), casting calls with full
context, drops/impact timing with written why, re-run + gate
calls. I NEVER bless: Deva citations, gloss meanings (M23),
per-chapter art, L3/L4, final ears. Revocable by deleting files.

## 6. How to use every other note

- RUNTIME: gospel, never edited. GATES: binary, eye+machine.
- STANDARD/VISUAL/CHAPTER-FORMAT: law; change only by owner
  call, same commit as code.
- PROCESS/PIPELINE/BLOCKS: chain reference; open deltas at
  PROCESS bottom are the known-gaps list.
- PROCESS_NOTES/PROCESS-NOTES2: how + wrong-vs-right + session
  record. BUILD-NOTES/EVENTS/REGISTRY: the log, the stream,
  the board — write as you go.
- MISTAKES M1–M27: read before touching renders or links.
- GOLD-STANDARD: v3 reference (predates persist-as-standard +
  b2 chant — future goldens diverge by owner call).
- IMPACT-FLOW: drop proposals (owner disposes) + NO-GROUPFINAL
  calls. LAYERS: translation sources (scholarship first
  resort; /tmp copy needs durable home). FISH-DIRECTION:
  voicing law + probe precedent. INTRO_BLOCKS/CHAPTER_PREP:
  working notes (folded). HANDOVER/READINESS/RENDER-PLAN:
  snapshots — trust REGISTRY + manifests instead.
- AGENTS/skills: entry + casting/cards references.
- DONE/TIMINGS/VISION/SPEAKER-RULES/archive/reviews/tools:
  frozen history or superseded method — read, never edit.
