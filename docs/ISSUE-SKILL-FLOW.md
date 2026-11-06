# ISSUE-SKILL LOOP — checker finds, skill resolves, notes close the loop

Clean flow, same schemas and drivers as everything else in the factory.
Cognition (builders, skills, agents) is untrusted; truth enters only through
deterministic gates on evidence; authority (owner bless/waiver) is an
explicit grant, never implied (qprivately A-COM kernel idea).

## The loop

1. **Run checker**: `python3 core/builders/check_issues.py <storyboard.json>
   [--out <unit>.issues.json] [--max 60]`. Runs bundle → V5b/V5c →
   audio-complete → list-geometry → verse-gloss-missing →
   verse-deva-no-english → stale-verse-hold → stack-crash → hold-scan →
   canon-shape → tts-ready (last two: shiva lane only; tantrasara
   finished/frozen), emits schema-validated
   `issues.json` (`core/contract/schemas/issues.schema.json`).
   Verse-card detail lives in `core/builders/check_verse_cards.py`
   (renderer-identical English decision + structural split spans) —
   see `docs/VERSE-CARD-CHECKS.md` for the anti-cheat story.
2. **Issue?** Each entry carries `kind` + `skill` (same name). Look up
   `core/skills/REGISTRY.json` → `core/skills/<kind>.md`.
3. **Skill known?** Apply its steps. `auto=true` (verse-term-unheld,
   missing-audio) runs unattended; `needs_owner=true` (gloss, Deva, draws,
   geometry restyle) files an owner request and waits.
4. **Re-run checker** to GREEN. The issue's `status` flips to `resolved`
   (or `waived-owner` with a waiver note) in the next `issues.json`.
5. **New kind?** Resolve it, write `core/skills/<new-kind>.md` + register
   in `REGISTRY.json`, same commit as the fix. A checker without a skill
   is a bug — fix the loop, not just the unit.

## Where it runs (runtime integration)

- `batch.py` STAGES open with `issues` (record-only, like `verify`): every
  unit writes `renders/issues/<stem>.issues.json` first, and the job log
  carries the open-issue count with skill pointers. Record-only never
  gates — downstream entries enforce, so audio for genuinely missing
  groups still renders.
- `run_queue.py --refresh` derives `needs-issues` from the artifact: any
  open `block`/`needs-owner` issue (unwaived, except `verse-gloss-missing`
  which ships Devanagari-only by law, and `missing-audio` which the batch
  audio stage renders before video entry re-verifies it) holds the unit
  there, so `--run-next` never launches blind. Absent file passes (checker
  has not run yet). `needs-draw` kinds never block launch: the renderer
  caps persists at 60s by law, hold-scan is advisory at video entry, H4 +
  ears dispose.
- Launch and `--resume` both call `require_issues_clear` live
  (`factory_contract.py`) — stale-registry launches are refused with the
  blocking issue ids + skill paths named.
- `batch` runs `validate_ship` as a record-only `validate` stage after
  `verify` (verdict `.ship.json` copied beside finals). It gates nothing
  pre-seal — ears + seal read the verdict later instead of re-deriving it.
- Ship mode (owner order 2026-11-06: get them rendered, no ears/seals
  required to ship, no whisper/voice-meter/H4-white blockage): `verify`,
  `validate`, and `voices` are record-only — their reports ship beside the
  final either way. Only real breakage stops a unit: missing/unrenderable
  audio, video entry gates, per-part prove (mechanical), failed concat,
  unconfirmed R2 byte-match (3 attempts).
- Freeze rule: builders, contract, storyboards, glossaries, approvals, and
  review packs are hash-pinned into every part at build time. Do not touch
  any of them while a batch runs — not even a comment, not even a note in
  an approval file — or in-flight and finished parts fail prove against the
  changed files and the run must restart. Docs, skills, registry, and
  tests stay editable throughout.
- Owner waivers: `renders/issues/<stem>.waivers.json`
  (`{version, waived: [ids], reason, date}`) flips named issues to
  `waived-owner`. Visible, never silent; re-running the checker preserves
  them.
- `run_blocks` video entry still calls bundle + audio-complete +
  list-geometry + hold-scan fail-fast (strict). `check_issues.py` is the
  same checks in planning form (estimates, no audio/video burns) plus the
  skill printout.
- `scan_holds.py` is the hold half of the checker (verse-term fix
  applied, >60s with reasoning). `preflight.py` is the V5/audio half.
- Skills never bypass gates: they prescribe draws, drops, Deva passes,
  gloss fills, restyles — the gate going GREEN is the close criterion.

## Current skills (14)

verse-term-unheld (auto, fixed) · missing-audio (auto: render_chapter) ·
white-gap / stuck-term / hold-scan-red (needs draw or waiver) ·
empty-gloss / machine-deva / verse-gloss-missing / verse-deva-no-english /
stale-verse-hold / stack-crash (needs owner) · canon-shape / tts-ready
(shiva-only; tantrasara finished/frozen) · list-geometry (needs restyle).

## Gate registry, success criteria, independent validator (anti-cheat)

- `core/contract/gates_registry.py --list`: every gate is a versioned pure
  predicate (`video/list-geometry-v2`, `ship/max-white-span-v1` …). New
  logic means a new gate id — never a silent edit (ipvv qp_gates pattern).
- `core/contract/success.py`: `tantrasara-ship-v1` — a unit ships iff EVERY
  criterion is TRUE on measured artifacts. UNKNOWN (missing evidence)
  schedules collection, never ships, never waives by default.
- `core/builders/validate_ship.py`: the qprivately-type checker. Reads ONLY
  measured artifacts (part hold entries, verify sidecars) — never storyboard
  estimates, never the estimator's code (import ban enforced by test). The
  builder cannot grade its own homework: entries are recomputed here (max
  white run with part-boundary merge, integrity sum-vs-duration and
  cuts-vs-entries), every verdict cites artifact SHAs as evidence, results
  are bool3 TRUE/FALSE/UNKNOWN.
- Batch now preserves the evidence: `renders/<stem>_parts/` (per-part
  render_metas + concat list) is copied beside finals before the transient
  sweep, and `entries` ship inside every new render_meta.

## Autonomy wiring map (what runs where — nothing here is manual-only)

Live chain (`chain_renders.sh` → `batch.py` waves): every unit opens
with the `issues` stage, which runs the FULL `check_issues.py`
(bundle → audio → geometry → verse-gloss-missing →
verse-deva-no-english → stale-verse-hold → stack-crash → hold-scan) and
writes `renders/issues/<stem>.issues.json` with skill pointers —
record-only, never gates (proven in the batch log: new kinds fire
unattended mid-chain). `run_blocks` video entry enforces bundle +
audio-complete + list-geometry fail-fast (+ hold-scan advisory);
`prove_clip` enforces prove gates; `validate_ship` records the
independent verdict beside finals. No human invokes any of this.

Operator loop (`run_queue.py --refresh` → `needs-issues` → `--run-next`;
`ralph_loop.py` check→skill→fix→re-check with registered auto-fixers):
`require_issues_clear` is the launch gate both read — open
`block`/`needs-owner` issues (unwaived, except verse-gloss-missing +
missing-audio) hold the unit, waivers release it. New kinds participate
identically: `verse-deva-no-english` and `stale-verse-hold` block until
scholar-fixed or owner-waived; `stack-crash` blocks until restyled or
waived (a build that would die mid-render must never launch blind).
`run_queue --refresh --dry-run` derives the board without saving;
`--run-next` launches one unit under the video lock and registers it.
`ralph_loop --dry-run` proves routing without touching series data
(locked by test).

Deliberately NOT in the live chain (by owner order, not omission):
draw filing (needs art + owner eye), reblocks (frozen-series rebuild +
rebless), bulk confirms (scholar/owner), Fish audio renders (cost).
The loop finds them, files them with skills, and waits — that waiting
IS the autonomy working, not a gap.

## Ralph loop (hardcoded autonomy)

`core/builders/ralph_loop.py --project <lane> --units <ids>` runs the loop
without coming back: check → skill lookup (+web-search prompt for novel
kinds) → registered auto-fixers (T1 gloss fill, Deva round-trip verify,
verse re-mine + ≥0.8 confirm incl. verse-deva-no-english, missing-audio
render) → re-check until no progress or `--max-iters` → full
tried/fixed/blocked report + launch verdict per unit (stale-verse-hold,
stack-crash, canon-shape, tts-ready block with skill pointers — no
auto-fixer by design). Novel kind with no skill file stops that unit as
`blocked-new-kind` (a human writes the skill same-commit as the fix — the
loop never invents law). `--dry-run` runs checkers only.

## Freeze rule (learned 2026-11-06 the hard way)

Builder/contract code and series data are hash-pinned into every part's
provenance at build time. Editing any of them mid-run silently invalidates
in-flight and finished parts (prove compares against current files) —
including APPROVAL files: never append notes to a hash-pinned file while
its unit renders; record blessings in REGISTRY/the log instead. Freeze
code+data for the whole unit run; docs/skills/tests/registry may still move.
