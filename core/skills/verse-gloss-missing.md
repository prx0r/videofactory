# verse-gloss-missing (needs owner/scholar)

Symptom: multi-line verse blocks have no `verse_gloss` entry, so the card
renders Devanagari only with no English literal/final underneath.

Diagnosis: `mine_verse_gloss.py` matches storyboard multi-line verses to
frozen T1 verses (similarity >= 0.5). No match means the storyboard chant
differs from T1 surfaces beyond the threshold (retelling vs frozen text,
or doubled Devanagari+IAST lines) — e.g. ch15: 4 multi-line verses, 7 T1
verses, best 0.37, 0 entries. Single-word chants are NOT this kind — they
resolve via glossary term cards (anu-case).

Fix: scholar reviews the unmatched pair (check_issues names the bids):
either approve the best match below threshold with a recorded reason, or
supply the literal/final from translation-work T1/L3 directly into
`verse_gloss_chNN.json` (frozen scholarship, match score recorded), then
bulk-confirm like glossaries. b2 (chapter-name chant, every chapter) is
excluded by the checker — never a T1 root verse. Re-run checker to GREEN.

Solved 2026-11-06 — ch15 0 entries → 1 (find→solve→notes):
FIND: `mine_verse_gloss.py ch15` printed NO MATCH best 0.37 for abhts_15.1
vs storyboard b53, although the texts are the same verse.
SOLVE (root cause): storyboard verse blocks carry DOUBLED
Devanagari+IAST lines (202 norm chars) while T1 surfaces are IAST-only —
`norm()` compared doubled to single, capping difflib at ~0.37. Fix per
multilingual fuzzy-matching best practice (Unicode NFD + single-script
normalization first, dedup doubled lines, preserve originals; cf. LREC
2026 Sanskrit Travelogue IAST-normalized indexing, sanskrit-lexicon
sanskrit-util layered keys, sa-embedding Devanagari-normalization gain):
`norm()` now uses the Devanagari half only (`split_scripts` → transliterate
→ fold). abhts_15.1 vs b53 went 0.37 → 0.97, entry mined with T1 literal,
bulk-confirmed under owner bless (T1 frozen scholarship). Remaining b234 /
b509 best 0.42/0.35 stay below 0.5 for scholar pairing — not forced.
Changed file: `~/tantrasara/mine_verse_gloss.py::norm` (one function);
re-ran only the 10 zero-entry chapters (existing matches untouched, no
remap churn). Factory check: `check_issues.py ch15` verse-gloss-missing
went 4/4 → 3/4 → 2/3 after the b2 exclusion.

Process note: 9 chapters still 0 entries (02,03,05-08,11-13) — most have
no multi-line root verses (all single-word chants → term cards, correct)
or need the same scholar pairing. Rendering without the entry is
Devanagari-only by construction, never a render bug — file the gloss,
don't touch the renderer.
