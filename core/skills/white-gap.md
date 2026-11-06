# white-gap (needs draw, owner disposes)

Symptom: `scan_holds.py` reports `WHITE_GAP Ns>60s` — no card up for over a
minute (subtitles moving does not count; talking head over empty white is
still a dead hold).

Diagnosis: no cue or event in the span. Common causes in order:
1. terms in the span are `proposed` (white by design until confirmed),
2. verse chanted a term but no cue fired (see verse-term-unheld — if the
   scan says `fixed path`, this cause is eliminated),
3. genuine exposition with no Sanskrit anchor.

Fix: file a sleepdrawn image (`propose_draws.py` → `draws_chNN.json`) that
reveals between two onsets inside the gap, per the 2026-11-05 60s law
(draws fade in between two onsets, staged like crisp/drops, never
auto-mutated holds). Shipped 01-13 are grandfathered; new renders 14-22+
must file per flagged gap. Scan must go GREEN or the gap must carry an
owner waiver before video.

Process note: scan names the block + seconds + nearest verse context.
Write the draw spec, re-run scan, record the draw id here.

Antidote (verified 2026-11-06, all 22 units, BUG 0 — see
`docs/WHITE-HOLD-ANTIDOTE.md`, saved verbatim): before filing a draw,
run `audit_white_gaps.py`. If it reports BUG, the engine missed a
holdable word — fix the engine, not the gap. If it reports PROPOSED or
UNLISTED or CLEAN, the white is honest: confirm, mine, or bless the
exposition — then file the draw for pacing, never as a cover-up.
