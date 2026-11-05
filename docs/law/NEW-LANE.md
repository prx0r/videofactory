# NEW LANE — render a new series (shiva pattern, 2026-11-04)

To render the shiva sutras — or any new work — follow the shiva lane
exactly. Builders stay single-copy; only lane paths are yours.

## 1. Scaffold (one-time, mechanical)

```
<repo>/shiva|yourlane/
  chapters/sNN.md        source units (one file per render unit)
  storyboards/           frozen storyboards
  overrides_sNN.json     casting calls as data
  glossary_sNN.json      terms, proposed until confirmed
  casting/               human-readable casting sheets
  review/sNN/            published packs + manifests + round notes
  assets/thumbnail/      series art (series.png fallback; empty = clean)
  split/casting/glossary/publish/run scripts (copy the shiva five, retarget)
  SHIVA-INTAKE.md        your lane log (decisions + unsure list)
```

## 2. Intake (autonomous, gates decide)

1. Split the dump: headings consumed in document order (assert exact
   count); boundary material attaches forward; appendices stay reference
   except explicit colophons; jacket/gmail/citation debris dropped (never
   prose). Reruns idempotent (`--only` scoping, M13).
2. Storyboard every unit through the shared builder. Validator green or
   nothing downstream runs.
3. Casting sheets → provisional auto-cast by tantrasara rules → owner
   blesses (UNCAST never defaults; remap by quote identity on resplits).
4. Mine glossaries (lane SKIP set) + title entries for the canonical
   header. All proposed.
5. Sheets for every unit (shared renderer proves holds green).
6. Publish review packs (lane R2 prefix). Manifests pin SHAs.
7. TTS hygiene sweep to tantrasara depth (welcome repeats, tails, silent
   shouts, tofu paths) + frozen-proof: rebuild the old lane and assert
   byte-identical before touching shared code.

## 3. Render (mechanical, gated)

Approval file per unit (owner act, cites the order, revocable) →
`run_all --chapters` (or lane runner) → verify → Qwen final (beats vs
transcript) → owner ears → seal golden → upload + HEAD verify. One video
build at a time (lock); preflight storage every batch; free Fish only
(dry-run ~$0.00, model string `-free`).

## 4. Wiring a lane into shared code (touch points, all documented)

- `holds.lane_for`: add the lane's glossary/verse/assets/thumbbox/numeral
  routing + `drops` path. shiva precedent is 12 lines.
- `intro_hold`: series fallback + maxbox already generic; numerals are a
  per-lane owner call (shiva pending).
- Render paths (`render_chapter`/`assemble_chapter` VOL dirs, R2 prefixes)
  still point at tantrasara — parametrize at render phase (open item,
  tracked in SHIVA-INTAKE.md, never worked around silently).

## 5. Never

New prose in sources, defaulted UNCASTs, silent shouts, Devanagari in
subtitle faces, folded keys as display text, unconfirmed layers in video,
self-granted approvals, concurrent video builds, local-disk renders.
