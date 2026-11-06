# empty-gloss (agent confirms T1-sourced; owner gate removed 2026-11-06)

Symptom: `validate_bundle` / preflight `V5b` fails:
`confirmed with empty gloss` (schema: `gloss does not match \S`).

Diagnosis: auto-mined term flipped to confirmed with no gloss
(tantrasara ch14-22 bulk-confirm postmortem: 61 empties).

Fix (owner only — agents draft `proposed`): fill the gloss from
translation-work T1/L4 via a sha-pinned drop, or flip the entry to
`proposed` (plays over white by design). Then republish the review pack
and re-bless approval SHAs. Factory `mine_glossary.py` writes
`proposed/` drafts and refuses to overwrite series glossaries.

Process note: preflight names the keys (first 3 + count). Do not bless
empties confirmed — the gate blocks by design.
