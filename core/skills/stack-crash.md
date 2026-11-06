# stack-crash (RETIRED 2026-11-06 — kept for old-build forensics)

STATUS: not a runtime gate any more. It is **retired**.

Why: the condition it guarded was a renderer bug. `build_clip` iterated
the word-level flat (which repeats every block once per word) and fired
one cue per matching word, so a single block chanting several long
compounds built a same-block stack that collided mid-render (ch16 p02).
The renderer now fires **exactly one cue per block** — the rule all
gates, scans, skills and tests already documented — so same-block
multi-cue runs cannot form and `require_list_geometry` models the
renderer exactly. Gate and renderer agree by construction.

`core/builders/check_stacks.py` remains in the tree as a forensic tool
for diagnosing old builds (it models the retired multi-cue rule and will
over-report against current code — never wire it back in without also
reverting the renderer rule).

Historical fix for a real old-build hit: split the list, shorten glosses,
demote a non-load-bearing term, or waive with an owner reason. See
`docs/VERSE-CARD-CHECKS.md` for the ch16 incident record.
