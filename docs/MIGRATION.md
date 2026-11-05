# MIGRATION — strangler path to the live factory (no big bang)

## Landed (this build)

- Structure: schemas, contract lib, proof helpers, CI workflow (codex).
- Builders: current master code + 2026-11-05 fixes (200-threshold chunking,
  chunked fallback, audio per-group guards, H6 word-row gate, ordered
  coverage, fail-closed preflight, no-rebuild board, PENDING_REVIEW queue).
- Repairs found while porting: voice_map.py prose lines uncommented (also
  broken in master — fixed here); run_all stage_board no longer rebuilds in
  place (could erase a blessing); check_voices returns codes (library-safe).
- Paths: every series location resolves via VF_REPO/VF_RENDERS/VF_R2
  (defaults = frozen system, parity by construction).

## Deliberately deferred (documented, not forgotten)

- `audio_mix_plan` is ported + tested but `_main_inner` still builds its mix
  inline (parity path). Rewire after a fixture A/B proves byte-identical
  mixes.
- Entry gates default to compat mode (log-and-continue) until packs are
  republished with view hashes; VF_GATES=strict is the cutover gate.
- Shiva lane publisher/render paths still point at tantrasara (NEW-LANE
  open item, unchanged).
- Assemble beds follow the clip table (PROCESS open delta, decided).
- S2 direction migration (FISH-DIRECTION) stays a versioned pending change.

## Cutover checklist (owner-ordered, in order)

1. check.py green including --strict.
2. Dry-run parity: factory builders print identical plans to frozen builders
   on all 22 chapters.
3. One sacrificial chapter end-to-end in the factory (audio cache reused
   read-only? No — factory renders to lane-configured volume paths; start
   with sheets + a 60s proof part, never a full chapter).
4. Owner reviews the proof part + this file, then lifts the freeze.
5. Cutover is a lane-config flip (drivers resolve factory core), never a
   file move. Frozen repos stay readable forever.
