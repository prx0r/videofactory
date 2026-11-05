# CHAPTER FORMAT — the fixed skeleton (every chapter, no exceptions)

Locked 2026-11-03. A chapter is a filled-in form, not a composition.
Every decision below was made once; the renderer makes none.

## The beats, in order

| # | beat | audio | screen | notes |
|---|---|---|---|---|
| 1 | bell | `bell_ding.wav`, +6dB, peak checked under 0dB | thumbnail (ch01 art; per-chapter art when supplied) | 0.99s attention grab. Kit lives in vatulanatha; pipeline references only. |
| 2 | title + role | granny, `[long pause]` tag | thumbnail holds | She speaks the chapter title, declares the role ("for this exposition I am..."), cold-opens. No title card ever. |
| 3 | overview | granny | thumbnail holds | What this chapter is about, plain. Ends with the handoff line ("Right — let's get into it" or chapter's own words, verbatim from text, never composed). |
| 4 | verse | verse voice, `[slowly]` | verse card (Devanagari only) up at first chanted word | The chapter's Sanskrit anchor (ch01: maṅgala). Clears the instant speech resumes. Subtitles IAST. |
| 5 | body | granny / man / verse per storyboard | term cards on mention, verse cards on chant, white otherwise | The chapters speak for themselves: narration, objections, dialogue, demonstrations, figures. Nothing added, nothing bridged. |
| 6 | outro | granny, next-chapter pointer | white | Spoken handoff only. (Note: STANDARD §3 says trailers kept — the scripts currently strip `Keep reading`/`Next:` lines. Flagged; owner to resolve.) |

Ch01 is the template: bell → thumbnail talk → handoff → maṅgala verse → body → outro. Every later chapter fills the same slots.

## The dumb-render contract

Render burns tokens (TTS, alignment, frames). It runs only on frozen inputs,
and it may only PASS or FAIL — never decide, never improvise, never "fix".

**Freeze checklist (all true before any render call):**
- `chapters/chNN.md` committed; word count logged.
- Intro budget: title + role + overview + handoff (verse excluded) ≤ 150
  words; recap after the verse ≤ 5 beats. No repeated greeting formulae —
  each chapter's handoff in its own words, never a series catchphrase.
  Current: ch01 110 ✓; ch06 217, ch14 179 — owner trims or grants exception
  (author's prose; machine never cuts).
- `storyboard_chNN.json` green: 0 errors, 0 warnings, validator run shown.
- `overrides_chNN.json` committed; every UNCAST resolved (validator proves zero).
- `glossary_chNN.json` committed; confirmed set listed by key. Proposed terms render as white — by design, not failure.
- Voice IDs + thumbnail asset path written in the chapter's log line.
- Storage preflight passed (local ≥1G, volume ≥4G).

**Then, mechanically, in order:** publish review pack (storyboard + timeline
+ sheets to R2) → owner approves (`approved_chNN.json`, SHAs pinned;
render REFUSES without it) → rough probes (`probe_rough.py`: the
Fish-mangle-prone blocks voiced cheaply, whisper round-trip on
English, Sanskrit-dominant + punctuation-heavy to owner ears and
Qwen — nothing renders until suspects are heard) → render → align
(means ≥0.85) → assemble (duration == sum of parts) → holds sheets → video →
COVERAGE printed (white target ≈20%, fail >85%) → verify_clip PASS →
Whisper head-check → Qwen taste-only → golden-check vs the blessed render
(duration ±2s, same cue order, cue times ±3s, white ±5pp) → upload +
HEAD verify → owner ears → seal golden → commit.

**Stop rule:** anything unplanned (new UNCAST, missing gloss, mean <0.85,
coverage fail, collision assert) halts the line. No retries with tweaks, no
token spend on guesses. Log it, plan it, re-freeze from step 1.

## Why this wastes nothing

Prosody is settled at storyboard (one TTS call per consecutive same-voice
section, content-hash filenames — re-runs are cache hits). Timing is
measured (MMS word onsets, gaps belong to the prior word — never estimated).
Cards are computed (cues from confirmed glossary, clamped spans — never
placed by feel). By render time there is nothing left to choose; the machine
only executes and checks.
