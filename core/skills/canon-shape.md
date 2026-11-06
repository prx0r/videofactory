# canon-shape (needs owner — reblock/rebuild, lane canon)

Symptom: a shiva unit's skeleton breaks the series canon
(CANONICAL-FLOW.md, Nov-4 owner verbatim): b1 title/ref spoken, the
sutra chanted, its IAST repeat, the literal gloss, then her funny
thing — same slots, every unit, so the ear always knows where it is.

Diagnosis (`core/builders/check_canon.py`, deterministic, shiva-only —
tantrasara storyboards are finished/frozen and no-op here):
- b1 must be title/granny (the ref header source; spoken-ref silence
  itself is engine-owned, noted never flagged),
- BOOK I/II/III marker title blocks exist iff the unit is s01/s23/s33
  (position-agnostic — s33's sits at b109),
- non-s00 units carry ≥1 verse chant; s00 carries none (no sutra in it),
- every multi-word Deva chant is followed within 2 blocks by its IAST
  repeat (key-matched, any voice — re-chant vs repeat is
  intent-ambiguous). Exempt by construction: self-contained bilingual
  blocks (Deva+IAST mixed, e.g. the s29 alphabet lesson) and cross-unit
  echoes (an IAST chant whose Deva aired in its home unit).
- "Literal:"/"Gloss:" labels never voiced (restructure stripped them).

Fix (owner act — storyboards rebuild deterministic from source): reblock
the span (join halves, restore the repeat, move the marker), rebuild
green 0/0, re-run checker to GREEN. Preservation law: reordering is
free; text edits are measured by word-multiset overlap and must keep
≥95% of the author's words (labels/junk stripped only) — anything
bigger is a restructure, not a finetune. The skill never authors prose:
it names the move, the owner/blessed rebuild makes it.

Process note: funny presence, literal quality, intro taste, and pacing
stay with owner/ears by design — this check owns skeleton + delivery
only. Bell policy, H1 silence, staged reveal, persist-by-default, and
ref-only headers are engine-owned (post-batch list), never filed here.
