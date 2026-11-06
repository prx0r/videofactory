# machine-deva (agent confirms T1-sourced; owner gate removed 2026-11-06)

Symptom: `validate_bundle` / preflight `V5c` fails:
`confirmed with machine/machine-lossy Deva`.

Diagnosis: Devanagari was machine-built — either folded-key conversion
(diacritics destroyed: ś/ṣ/ṇ confusion certain, M15/M23 malpractice) or
unreviewed transliteration. Tantrasara ch14-22: 689 terms bulk-confirmed
2026-11-05 from `machine-deva fill` output.

Fix (owner only): Deva pass per akshara against the IAST citation. Clean
IAST sources convert deterministically and reversibly:
- translation-work `tantrasara-aNN/SOURCE.txt` + `T1-*.jsonl` (frozen T1),
- ipvv `works/ipvv/passages.jsonl` + `work.json` (`sanskrit` fields, IAST
  with diacritics → Devanagari via `indic_transliteration`, same as
  `holds.to_deva`).
IAST→Devanagari is trivial for these listings; the review is the work,
not the conversion. Record Deva via a sha-pinned drop (LAYERS: card data
enters only through versioned drops, never hand-copied strings), set
`deva_status: owner`, republish + re-bless. Never flip machine rows to
`owner` without reading each akshara.

Anti-cheat lesson 2026-11-06 (ch20 `anandamrta-…` precedent): NEVER verify
Deva by round-tripping through folded ASCII — fold erases exactly the
confusion class under test (ś/ṣ/s, ṇ/n, ṛ/r), so garbage verifies clean.
A valid check needs a diacritic-bearing source (Devanagari or fully-marked
IAST from T1/author surface) and byte-exact equality against
`to_deva(source)`. Diacritic-less ASCII transliterated and compared proves
nothing. The agent may confirm ONLY this strict form (`machine-verified`
+ source named); anything weaker stays proposed.

Process note: preflight names the count + first 3 keys. Current state
(ch01-13 `legacy|confirmed` clean; ch14-22 ~689 machine) is the baseline;
this skill closes when preflight V5c is GREEN for the unit.
