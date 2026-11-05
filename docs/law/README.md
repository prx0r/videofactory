# LANE-APPLICATION — how the ported law applies in the factory

The docs in this directory are verbatim copies of the frozen series law
(2026-11-04/05). They are READ-ONLY references: amend them only by owner
call, same commit as the code, in the series repo first, then re-port.
This file records how each law applies to factory paths and lanes. Where
this file conflicts with a law doc, the law doc wins and this file gets
fixed.

## Path mapping (every doc that names a path)

- `~/tantrasara` (repo) → `VF_REPO` (series config). Builders resolve via
  `core/contract/paths.py`, never literals.
- `~/vol/tantrasara/renders` → `VF_RENDERS`. Renders go to the lane volume.
- `r2:svread-audio/tantrasara[/review]` → `VF_R2` (+ `/review`).
- `storyboard_chNN.json` (ch06: `storyboard_ch6.json`) → tantrasara lane
  only. Shiva lane: `shiva/storyboards/storyboard_sNN.json`, glossaries
  `shiva/glossary_sNN.json`, drops `shiva/drops_sNN.json`.
- `/tmp` fixed paths (mmsclip, clip_frames, stage_*, video lock) are
  unchanged: one video build at a time, lock as code (BARS 22).

## Per-doc deltas

- RUNTIME: gospel + dated amendments in one log (chunk video supersedes
  mux-once-whole, owner-ordered 2026-11-04). The driver state machine
  implements the routine; PENDING_REVIEW waives byte-identical rebuilds.
- STANDARD: all 17 sections hold; §2 voices per series config (same seats
  until a series casts its own); §14 storage via preflight (fail-closed).
- VISUAL: screen canon holds for every lane; per-lane params via
  `holds.lane_for` (thumbbox, numeral True/False, art_center, header
  shape). Shiva: ref top-right + title top-left from the unit itself.
- GATES: binary list unchanged; H6 word-row match enforced by gate_visual;
  machine lines run per part, eye lines off proof PNGs with filed notes.
- GOLD-STANDARD: ch01 v3 reference recipe; per-series goldens sealed the
  same way (tolerances identical).
- PLAYBOOK/PIPELINE/PROCESS/BLOCKS: chain reference; builders are
  `core/builders/` now, behavior identical (parity-proven). Entry gates
  run in VF_GATES mode (compat default, strict at cutover).
- LAYERS: translation layers enter ONLY through versioned sha-pinned drops
  (never hand-copied strings). Card layers unchanged.
- CHAPTER-FORMAT: the six beats are per-UNIT (see UNITS.md); intro budget
  150 words, recap 5 beats; freeze checklist + stop rule unchanged.
- FISH-DIRECTION: v1 tags canonical now; S2 migration versioned with
  byte-proof + re-voice cost (never mid-batch).
- VISION: intent template; per-series §2–§5 filled by owner (R1: agents
  never author).
- NEW-LANE: superseded by series/_template + new_series.py (same steps,
  scaffolded).
- PROCESS_NOTES/PROCESS-NOTES2/MISTAKES: session record + wrong-vs-right +
  scar log; live continuation of M-numbers happens here on new failures.
- SPEAKER-RULES: superseded for casting (seats live in STANDARD §2 /
  series config); ritual shape kept.
