# list-geometry (auto: akshara wrap; owner restyle only if that fails)

Symptom: `require_list_geometry` / `render_list` fails:
`conveyor collides with subtitle zone` / `slots overlap` / `column overflow`
(ch15/ch21 precedent: 160+ block ranges with long-gloss stacks died
hours into video).

Diagnosis: a confirmed-term window does not fit its slot — usually a long
unbreakable Devanagari compound (30-40 chars, no spaces) in a narrow
corner/triangle slot, or a tall multi-line card over the subtitle zone.

Fix (automatic, no law change): `holds.wrap_lines` breaks overlong
Devanagari tokens between whole aksharas — never inside a conjunct, never
detaching a dependent sign, never stranding a danda (W3C Devanagari layout
requirements §8.1 + UAX #14 ZWSP-as-break-opportunity, applied as a
renderer rule). Web search ruled out the alternatives: morpheme splitting
needs a full sandhi parser (ambiguous, would invent breaks — rejected),
CSS-style anywhere-breaking would split conjuncts (W3C-forbidden), and
`sa-embedding`/`sanskrit-lexicon` guidance says normalize to one script,
never guess. Sizes, positions, colors unchanged; only line positions move.
Re-run the gate after any renderer change.

Fix (owner): if a run STILL collides after wrapping (bottom-slot stacks
taller than the 240px budget allow — dense literal + gloss under a wrapped
Deva), that is a genuine restyle case: split the list, shorten gloss
bodies, or approve a smaller floor. The agent must NOT demote terms or
shrink type unilaterally to clear the gate — that is cooking, not fixing.

Solved 2026-11-06: ch16 run [muladharad, prasrta-…, nasa-gagana…, viksipan]
(3-stack triangle, 640px) and ch20 run [devya, anandamrta-nirbhara-…, tvam,
devya] (pair, 780px) both rendered after wrapping, verified by re-running
the gate — zero data changes, zero restyle. Precedent false positives
(ditto: one-cue-per-block mirroring, literal-gating mirroring) are recorded
in the gate docstring; the rule is the renderer is always right.
