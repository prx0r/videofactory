# FISH DIRECTION — how to voice the line well (S2 / s2.1-pro-free ONLY)

Scope: Fish `s2.1-pro-free` on the compat endpoint, S2 `[bracket]` cues.
Drama-3 is a different model with different tags — never used here, never
referenced in directed text. Free tier only, always (`tts_line.py` pins the
model; dry-run must print ~$0.00 and `-free`).

Source: https://docs.fish.audio/developer-guide/core-features/emotions.md
(imported 2026-11-04; S2 syntax section only).

## The pause stack (in order — every layer earns its place)

1. **Terminal punctuation (source law).** Every voiced block ends with
   `. ! ? … : ; —` (or Sanskrit `। ॥`). Blocks join with a bare space at
   render, so an unterminated block reads straight into the next one as a
   single breath — the s00 run-on ("...Donut The Way of Śiva...") was
   exactly this. Audit: scan storyboards for narration/title blocks whose
   last char is not terminal; fix SOURCES (never storyboards), skip quotes
   (author's speech is verbatim — list them for the owner), skip Deva
   (verse engine owns it). Rebuild; IDs don't shift; no remap needed.
2. **Beat tags (whole-block lexicon).** `BEAT_LEXICON` in
   `build_storyboard.py`: interjections and punch lines that earn a
   `[break]`. Ordinary short sentences are NOT beats — tagging them all
   turns direction into wallpaper (house rule, both lanes). Whole-block
   match or colon-ender only. Compare beat RATES across lanes when
   something feels flat (tantrasara 8.7% vs shiva 4.3% was content, not a
   gap — proven by identical tagging of the same words in both lanes).
   Lexicon changes re-voice every chapter containing the word — never
   mid-batch, always with byte-proof.
3. **Title weight.** Titles carry `[long-break]`. Spoken scaffolding
   (refs, book markers) is silenced by lane rule instead of tagged —
   never make the voice say what the screen already shows.
4. **Drops and beds (engine).** Dramatic holds come from
   `drops_sNN.json` (`{bid: {pause, why}}` — unjustified silence never
   renders) and the deterministic bed table in `build_clip.py`. Drops
   split groups (content-hash misses, automatic re-render). Owner proposes
   positions; engineer encodes.
5. **Audit invariant.** Stripped directed text must equal the original
   (`audit_direction`) — tags prefix, bodies are never rewritten.

## Adopted S2 markers (and only these)

- `[break]` — beat pause (granny catchwords, dialogue turns).
- `[long-break]` — title/handoff weight (replaces the old
  `[long pause]`/`[short pause]` natural-language cues post-batch;
  re-voices everything, so the swap ships with the byte-proof).
- Seat emotions (one primary per sentence, ≤3 combined, cue at sentence
  start, never wallpaper): granny wry on funny lines (`[sarcastic]` where
  the joke needs it, never on exposition); verse chants bare (no tags —
  purity); man skeptical where the line challenges (`[doubtful]` sparingly).
  Emotion tags change directed text = re-voice; shiva is unrendered so
  the cost is previews only.
- Never: paid models, drama-3 tags, `(parens)` S1 syntax, tags on verse
  chants, emotion on every sentence.

## Prove it (every direction change) + rough probes (every chapter)

`probe_rough.py` voices the Fish-mangle-prone blocks before any
chapter render: IAST/digits/punctuation/short-fragment scoring,
whisper round-trip on English-dominant blocks, Sanskrit-dominant
and punctuation-heavy always to owner ears with wav clips
(whisper garbles short Sanskrit by design — scores there prove
nothing). Nothing renders until suspects are heard.

1. Rebuild green, 0/0. Diff same-text voices (only intended changes).
2. Re-voice affected groups only (content-hash cache proves the rest).
3. MMS means ≥0.85, zero nonmono (tags never reach the aligner — it reads
   `b['text']`, not directed; verify the assert holds).
4. Whisper head-check (words present, in order), then owner ears.
5. Log the rate comparison + the decision in the lane INTAKE file.

## Worked cases (this lane)

- s00 run-on: subtitle headings carried no periods → 40-word breath.
  Fixed at source (118 narration blocks lane-wide), zero quotes touched.
- M17: `॥१॥` crashes sa-IN (`RomanizeError`) — verse blocks carry words
  only, digits live in the header ref.
- Scaffolding laugh: b1 ref + b2 book marker spoken back-to-back with the
  chant — silenced by lane rule, zero re-voice (groups vanish, hashes kept).

## Remap law (casting survives text work)
Voice calls live in quote text, not block IDs. After any source change,
re-anchor by quoted-span identity and prove zero drift before rebuild.
See M18 — three "green" remaps silently unvoiced quotes.
