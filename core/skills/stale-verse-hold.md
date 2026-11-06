# stale-verse-hold (needs owner — reblock is a frozen-series rebuild)

Symptom: instead of the just-chanted verse holding, the card switches
Devanagari back to an older/different verse — a regenerated or half-verse
Deva persists through the following narration.

Diagnosis (`core/builders/check_verse_cards.py`, structural, no timing
estimates): one Sanskrit verse is scattered over several storyboard
blocks, so no block matches the full-verse `verse_gloss` key and at least
one block's card Deva is machine-regenerated. Structural signatures
(detector prints the pattern per span):
- `split-label` — a verse block carrying a bare `TRANSLITERATION` /
  `IAST TRANSLITERATION` / `ORIGINAL SANSKRIT` line (the split marker;
  e.g. ch16 b822, ch18 b690, ch20 b1930). The halves live in neighbours.
- `same-key-pair` — adjacent verse blocks with EQUAL `verse_match_key`
  but different bids (same verse, two cards — key equality via the shared
  `holds.verse_match_key` is proof, not heuristic; e.g. ch19 b304/b305).
- `roman-only-verse` — a >3-token IAST-only verse block, or a short one
  sitting inside a labelled split (e.g. ch16 b823, ch20 b528). Its card
  Deva comes from `to_deva(IAST)`, never the author's citation, and its
  fragment key can never hit the full-verse gloss entry.
- `iast-tail-misvoiced` — a granny/man block (mostly IAST: ≥2 diacritic
  tokens, ≥50% of tokens, ≤12 tokens, adjacent to a verse-tagged block or
  a chained tail) that continues the verse (e.g. ch16 b824, ch19 b199,
  ch20 b1931/b1932 chained). The tantrasara caster's every-token-Sanskrit
  rule sank on one ASCII word (`kim`, `adbhutam`, `mucyate` are not in
  the 11-word `SANSKRIT_LEXICON`), so the tail fell through to granny —
  Fish granny then reads Sanskrit with an English voice while the card
  holds stale. TANTRASARA-ONLY pattern: shiva canon voices the IAST
  repeat with granny by Nov-4 owner call, so tails are not flagged there.
Pure single+single same-key pairs (an IAST term plus its Deva, e.g. ch16
b243/b244) are term re-chants, not splits — excluded here; they stay under
glossary/audit discipline.

Fix (owner act — storyboards are frozen; change rules/overrides and
rebuild, never hand-edit): reblock each span into whole verses — join the
halves into one verse block carrying the author's Deva (drop the label
line from the text; labels are markers, never chant), move the IAST tail
back to verse voice, rebuild the storyboard (0 errors 0 warnings), then
mine/confirm the full-verse gloss (now the key matches) and re-run the
checker to GREEN. The paired `verse-deva-no-english` issue on the same
bids clears with the same rebuild.

Process note: the renderer itself always holds the NEWEST chant
(`build_clip` newest-persist-wins + 60s cap), so a stale card always
traces to fragmented verse data, never to hold selection — fix the data.
>60s timing fallout on these spans is already filed as `white-gap` /
`stuck-term` (draws per the 60s law); this kind owns the reblock.
