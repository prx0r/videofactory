# Verse-card checks — process notes (owner bugs, found 2026-11-06)

Two bugs the owner caught by eye on unrendered units, now caught by the
checker the same way every other bug is: find once, gate forever.

## Bug 1 — verse-deva-no-english

A verse card ships Devanagari with no English literal/final underneath.
Root cause is not one thing but five shapes with one renderer rule:
`holds.render_hold(confirmed_only=True)` — exactly what `build_clip`
passes — shows verse-gloss English only from a CONFIRMED entry keyed by
`verse_match_key(block text)` (literal or final present), or full term
layers for a ≤3-token chant hitting a confirmed glossary term. So a card
is English-less when its gloss entry is missing, proposed, bids-stale
(entry names bids its `match_key` no longer matches), label-polluted (a
bare `TRANSLITERATION` / `IAST TRANSLITERATION` line inside the block
poisons the key), or a split-off roman half (fragment key vs full-verse
key). `verse-gloss-missing` (bids-membership) sees only shape 1; the new
check replays the renderer's key decision, so it sees all five.

Script: `core/builders/check_verse_cards.py` — `confirmed_views()` builds
the exact `_gl` / `_vg` views `build_clip` builds (confirmed terms with
gloss, literal only when `literal_status` is confirmed; verse_gloss keyed
by `match_key`), `card_english()` replays the English branch,
`find_no_english()` flags verse blocks (≠b2, multi-line or split-member)
with no English. Single-word chants outside splits stay under
glossary/audit discipline (`audit_white_gaps` UNLISTED = mining backlog).

## Bug 2 — stale-verse-hold

Instead of the just-chanted verse holding, the card shows an older or
regenerated Devanagari through the following narration. The renderer
always holds the NEWEST chant (newest-persist-wins + 60s cap), so a stale
card always traces to fragmented verse data: one Sanskrit verse scattered
over Deva block + roman-only half + granny/man IAST tail. Signatures
(`find_split_spans`, no timing estimates):
- `split-label` — bare TRANSLITERATION label line in a verse block,
- `same-key-pair` — adjacent verse blocks with EQUAL `verse_match_key`
  (same verse, two cards; key equality via shared `holds` is proof),
- `roman-only-verse` — >3-token IAST-only verse block, or a short one
  inside a labelled split (card Deva is `to_deva`-regenerated, never the
  author's citation),
- `iast-tail-misvoiced` — granny/man block, mostly IAST (≥2 diacritic
  tokens, ≥50%, ≤12 tokens), adjacent to a verse span or chained tail
  (the caster's every-token-Sanskrit rule sank on one ASCII word such as
  `kim`/`mucyate`, absent from the 11-word SANSKRIT_LEXICON, so the tail
  fell through to granny — Fish granny then reads Sanskrit).
Pure single+single same-key pairs (IAST term + its Deva, e.g. ch16
b243/b244) are term re-chants, excluded — newest holds correctly there.
Canonical instance: ch16 b822/b823/b824 (all three patterns in one span).

Script: same file. Fix is a reblock (frozen series: rules/overrides +
rebuild, owner act), then mine/confirm the full-verse gloss. >60s timing
fallout on these spans is already filed as white-gap/stuck-term (draws).

## Findings on 16–22 (2026-11-06, point-in-time)

no-english verse cards (49): ch16: 4 (b316 proposed, b348/b822 missing,
b823 half) · ch17: 6 (b146/b176/b356/b449/b571 missing, b205 proposed) ·
ch18: 11 (9 missing incl. b65/b690-label, b113 proposed, b691 half) ·
ch19: 8 (all missing — zero verse_gloss entries) · ch20: 5 (b527/b567/
b1299 proposed, b1097/b1930-label missing) · ch21: 9 (5 missing, 4
proposed) · ch22: 6 (4 missing, b869/b1029 proposed).
stale spans (28): ch16: 1 · ch17: 3 · ch18: 1 · ch19: 5 · ch20: 5 ·
ch21: 7 · ch22: 6. Full bid lists: `check_verse_cards.py <storyboard>`
(issues.json entries cap blocks at 6 by convention).

## How this is 100% validated (anti-cheat)

1. Shared implementation, never re-implemented: keys via
   `holds.verse_match_key`, Deva splitting via `holds.split_scripts`,
   transliteration via `holds.to_iast`, lane/glossary resolution via
   `holds.lane_for` — the same functions the renderer calls. A change to
   any of them moves checker and renderer together; drift is impossible.
2. Image-level parity tests (`tests/test_verse_cards.py`, RendererParity):
   the REAL `holds.render_hold` (the single implementation sheets and
   video share) is sensitive to a verse_gloss entry iff `card_english`
   says English is present, and ignores `proposed` entries exactly as the
   checker predicts (`ImageChops.difference` pixel-equality). A renderer
   change to English layering breaks these tests instead of desyncing.
3. Deterministic, no estimates: both checks are textual + key-based. No
   WPM, no timing, no model verdicts — reruns are byte-identical.
4. Loop-closed: `check_issues.py` steps 5b/5c emit schema-validated
   `verse-deva-no-english` / `stale-verse-hold` issues (needs-owner, skill
   pointers), `require_issues_clear` holds launches until waived/resolved
   (12 tests in `tests/test_verse_cards.py`, full suite 136 green,
   `check.py` CANONICAL).
5. Honest boundaries, stated in the skills: singles outside splits are
   UNLISTED backlog (audit owns them); Deva+IAST term pairs are re-chants
   (glossary owns them); the checker proves what it flags and names what
   it does not.

## Queued post-drain (NOT done — provenance-pinned files)

- Promote to fail-closed video entry (`run_blocks` + `factory_contract`
  `require_*`): `build_clip.py`, `holds.py`, `factory_contract.py`,
  `run_blocks.py` entry gates are hash-pinned into in-flight part
  provenance — no touch while the 15–22 chain renders. Until then the new
  kinds are record-only in batch (like verify/validate) and hold
  `run_queue` launches at `needs-issues`.
- Owner call: add `verse-deva-no-english` to `require_issues_clear`'s
  nonblocking set (like `verse-gloss-missing`, on the grounds that
  Devanagari-only cards are the law-compliant baseline shipped on 01–13)
  or keep it blocking scholar work. Currently blocking-by-default.

## Fix run 2026-11-06 (then re-run — deltas below)

`ralph_loop.py --units 16-22` (wired: `verse-deva-no-english` →
mine+confirm ≥0.8 fixer; `stale-verse-hold` → explicitly blocked):
miner confirmed **0** new entries ≥0.8 on all 7 units — the missing
pairs are genuinely below the fuzzy bar (scholar pairing, cf. b234/b509
precedent), not a miner gap. `fill_glossary_t1 --chapters 16-22 --apply`
(owner-ordered, T1-only, never invents): **0 filled, 0 new** — T1 l0 has
no gloss for the 387 remaining proposed/unlisted terms. Root causes
closed: (1) verse gaps need scholar pairs/confirms from non-T1 sources;
(2) glossary gap needs scholar definitions; (3) splits need owner
reblocks. Re-run checker output is identical in kind counts
(125 issues: 7+7 verse kinds, 28 stale spans, 83 timing spans) —
deterministic, nothing silently fixed, nothing silently broken.

## Incident same run (freeze violation, fail-closed caught it)

The fix run edited 16–22 data (verse_gloss remines, glossary rewrites,
approval refreshes) while the live chain was building ch16 p00
(10:10–10:21). `glossary_ch16.json` rewrite proved byte-identical
(MATCH), `storyboard` MATCH, but `approved_ch16.json` refresh #2 changed
the pinned approval bytes after p00's provenance was computed → p00 will
fail `validate_clip_artifacts` loudly at prove. No other part is
affected (p01+ built on post-edit files; ch14/ch15 files untouched —
mtimes verified). Remediation per precedent (wipe + relaunch clean),
post-drain ONLY (lock held across units — never touch a live build):
`rm -rf ~/vol/tantrasara/renders/ch16_blocks` then
`batch.py --project tantrasara --units 16 --ship`. Owner queue:
`/tmp/owner_queue_16_22.json` (28 reblock spans with bids/patterns;
83 draw-or-waiver specs with seconds). FREEZE: no series-data or
provenance-pinned edits until the 15–22 chain drains.
