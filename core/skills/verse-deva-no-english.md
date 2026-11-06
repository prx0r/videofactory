# verse-deva-no-english (needs owner/scholar)

Symptom: a verse block's card renders Devanagari with no English
literal/final underneath — the owner asked English under all Devanagari.

Diagnosis (`core/builders/check_verse_cards.py`, renderer-identical):
`card_english` replays the video renderer's own English decision
(`holds.render_hold`, `confirmed_only=True`, i.e. exactly what
`build_clip` passes). A card carries English only from a CONFIRMED
`verse_gloss` entry (literal or final present) keyed by
`verse_match_key(block text)` — the shared `holds` helper, never a
re-implementation — or, for a ≤3-token chant, from a confirmed glossary
term's layers. Everything else ships Devanagari-only:
1. no `verse_gloss` entry at all (mine from T1/L3, then bulk-confirm),
2. entry `proposed` (confirm it — video shows confirmed only),
3. bids-stale entry (re-mine: the entry names bids but its `match_key`
   no longer matches the block text, so the renderer lookup misses),
4. label-polluted key (the block carries a bare `TRANSLITERATION` /
   `IAST TRANSLITERATION` / `ORIGINAL SANSKRIT` line, so its key can never
   match a full-verse entry — fix under `stale-verse-hold` first),
5. split-off roman half (the half's key is a fragment of the full-verse
   key — fix under `stale-verse-hold` first).
b2 (tantrasara chapter-name chant) is excluded — shiva b2s are real
sutra chants and are checked like any other verse block (lane-aware
exclusion, same rule in `verse-gloss-missing`). Single-word chants outside splits stay
under glossary/audit discipline (`audit_white_gaps.py` UNLISTED = mining
backlog, not a bug).

Fix: scholar pairs each named bid (checker prints all): mine the T1/L3
literal/final into `verse_gloss_chNN.json` (frozen scholarship, match
score recorded) or bulk-confirm the proposed entry, re-run the checker to
GREEN. Split members (named in the paired `stale-verse-hold` issue) need
the reblock first — confirming gloss against a half-key never lands.

Solved-shape precedent 2026-11-06 — ch15 0 entries → 1 (`mine_verse_gloss`
`norm` fix, single-script Devanagari-half normalisation, 0.37 → 0.97):
normalisation bugs hide here too. If a same-text verse has no entry while
its twin does, suspect the key (label line, doubled Deva+IAST lines), not
the miner — file under `stale-verse-hold`.

Process note: single-word chants with no glossary term are deliberately
out of scope (UNLISTED backlog). `audit_white_gaps.py` owns them.
