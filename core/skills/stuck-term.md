# stuck-term (needs draw/overlay/release, owner disposes)

Symptom: `scan_holds.py` reports `STUCK_TERM key Ns>60s` — one term card
held for over a minute with no superseding cue or event.

Diagnosis: single anchor with long exposition and nothing later to clear
it (no next cue, chant, or tone break). Correct-by-data but unwatchable
past ~60s.

Fix: same as white-gap — file a draw/overlay/release that lands inside
the stuck span (clear the hold first via cue/drop, then draw, per staging
law: draws start on white blank, never straight off a Sanskrit card).
Alternatively the owner may bless the stuck hold (golden) with a waiver
note. Never auto-mutate holds to satisfy the timer.

Process note: scan names the key + span + block. IMPACT-FLOW.md in
tantrasara is the precedent log (stuck `diksa` 125s, `sambhu` 136s with
PROPOSE follow-ups). Record the draw id or waiver here.
