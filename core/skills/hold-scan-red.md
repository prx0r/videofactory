# hold-scan-red (aggregate: file draws or waive)

Symptom: `scan_holds.py` exits RED / `require_hold_scan` raises:
`hold scan RED past 60s` with per-gap lines.

Diagnosis: aggregate of white-gap + stuck-term above. The scan already
applies the verse-term fix, so remaining RED is genuine: needs draws
(60s law, owner call 2026-11-05) or owner waivers (shipped 01-13
grandfathered, goldens exempt by blessing).

Fix: for each FAIL line, follow its kind skill (white-gap →
`white-gap.md`, stuck-term → `stuck-term.md`). File
`draws_chNN.json` entries or record waivers, re-run scan to GREEN.
Video entry (`run_blocks`) refuses while RED — by design, so long holds
can never ship silently.

Process note: scan output is the work list. Record draw ids/waivers per
unit here; the checker going GREEN is the close criterion.
