# gif-choose (how to pick the perfect GIF for a passage)

One visual system: every GIF arrives with its etched first frame, the pen
draws it for as long as the passage needs, then the motion plays. Choosing
well is what makes the etch worth watching — the drawing earns the movement.

## The recurrence rule (house law, VISUALS.md)

A moving emblem is earned ONLY by recurrence across beats or units. Count
first: `process/gif-placements.md` in each lane holds the evidence
(motif → hit counts → example bids). A motif with hits across beats or
units graduates to GIF; a single-use image stays a draw or still, never
a GIF. Counter-examples live in the placements file under "Demoted to
draw" — respect them.

## Choosing (in order)

1. Read the passage. Name the ONE image the passage keeps returning to
   (the dog at the water, the whirlpool, the lamp going out).
2. Check the bank first: `vf_motion` (or `core/art_bank/motion.json`).
   A banked GIF with your motif means the choice is made — wire it, don't
   invent. `used_in` tells you which lanes already play it; reuse across
   lanes is normal (the bank is shared).
3. If the motif is wanted but unbanked, check the unit's
   `process/pending-clips.json` — the bids and time estimates are already
   there. Arrival triggers assignment, not deliberation.
4. If the motif is nowhere (not banked, not wanted, no placement hits):
   it is probably a draw, not a GIF. File it as a draw gap. If you believe
   it recurs, gather 3+ beat citations and propose it as a new wanted entry
   with a maker brief (see gif-request), same commit as the placements
   evidence. Never render a one-off as motion.
5. Match the lane voice: nibbana is English-only (no text in frame ever),
   paratrishika wants letters and hearts, tibetan-dead wants deities and
   bells, deathworks wants judgment and departure. A perfect GIF in the
   wrong lane is a wrong GIF.

## Placement

Prefer beats where the text performs the motif, not merely names it — the
dog chapter plays over the fight, not over the word "dog". Passage mode
(`storyboard` + `from_bid`/`to_bid` in vf_seamless_draw) times the etch to
the buildup and lands the motion on the payoff; a hard keyword hit is the
last resort, never the default. Etch length is free (30s to 3min+); the
motion runs 2x ~20s unless a ramp says otherwise.

## Verify

After wiring: `draws_for`/`clips_for` accept the files (white-start,
complete-after-start, asset exists, why present), the gate stays green,
and the catalog shows the unit thumbnail. Then it is chosen. Until then
it is a suggestion.
