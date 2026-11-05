# SPEAKER RULES — v0 (2026-10-29, intake: cast TBD by owner ear)
# SUPERSEDED 2026-11-04 for voice casting: seats locked in STANDARD.md §2
# (granny / man 75% / verse, Fish s2.1-pro-free) and implemented in
# `build_storyboard.py` + the `tantrasara-storyboard` skill. Kept for the
# ritual shape (§Per-section order, bells) which still applies.

The archive voice (whoever reads + explains this text) is BOTH voices
already: readings AND explanations.

## The seats (structure fixed; cast per text)

1. **ARCHIVE (untouched)** — every spoken teaching clip. Inside beats it
   both reads the text and explains it; the assembly never splits a clip.
   It owns ALL sacred-language-aloud (Sanskrit verses) — no other voice
   touches it.
2. **GUIDE (TTS)** — two jobs: the section question at every ritual open,
   and the plain-English RESPONSE in every section opening. Candidate
   voices trialed per text (reference: kid asks, old man answers);
   owner picks by ear from a one-file audition. Backup voice named at lock.
3. **HUMAN (owner)** — section intros + rare marked bridges. No sacred
   language; no verses.

## Per-section order (identical everywhere — the listener learns it once)

motto bell → guide asks → recollect (3s default; U1 5s in the reference
build — set per text in rhythm.json) → guide gives the plain →
breath → essay-0 verbatim on screen + archive pointer → beats →
zoom bell. Nothing wedges between question and plain, or plain and essay-0.

## Bells (build/assets/ — ported kit, fixed)

- **Motto bell** (bright, 2.5s): refrain moments + every section open.
- **Zoom bell** (low + sub octave, 6.0s): section thresholds only.

## Hard rules (violations fail the build)

- No invented sentences in the guide's mouth — script or glosses only.
- No sacred-language tokens in TTS lines (scan: diacritics, leading chunks,
  inline terms carry immediate English glosses).
- No voice overlaps another; pauses are separate events in the manifest.
- Verbatim is extracted, with provenance — never typed.
