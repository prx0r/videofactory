# cue-model (law, not a defect kind)

One sentence, and every gate depends on it:

> **The video renderer fires exactly ONE term cue per block — the first
> matching word — for narration, dialogue AND verse.**

This is the single normative rule. `build_clip`, `gate_visual` (H3),
`gate_storyboard` (H8), `require_list_geometry`, `scan_holds`,
`audit_white_gaps` and every test all implement this same rule. If any
one of them drifts, it either invents defects (false alarms that stall
renders) or misses real ones.

History: build_clip once fired a cue per matching WORD because its flat
list repeats a block once per word and the loop re-scanned. That drove
unrenderable same-block stacks (ch16 p02) and made every one-per-block
gate blind to them. Fixed 2026-11-06 by breaking after the first cue per
block id. Re-mentions across different blocks still fire (each block
cues once) — the list-stack engine still accumulates across blocks.

Changing this rule requires changing ALL of the above in the same
commit, plus the `cue-model` test in `tests/test_stacks.py`.
