# LAYERS — every layer documented, sourced, gated (2026-11-04)

Two stacks feed the screen. Translation layers live in
`/tmp/translation-work/tantrasara-aNN/` (frozen T1 batch 2026-10-30;
FLAG: tmpfs, not durable — needs an R2 tarball like the MMS deps
before anything depends on it blindly). Owner rule 2026-11-04:
scholarship questions go to these translations first.
Card layers live in `glossary_chNN.json` + `verse_gloss_chNN.json` and
render from `holds.py`. Nothing floats: each layer points at its source.

## Translation layers (translation-work)

- **T1** — fast token-gloss stream per verse (`T1.md`, frozen). All 22
  chapters present. Feeds our literal drafts. Status: frozen batch,
  machine-proposed.
- **L0** — scholarly audit with meaning-forks (`T1.l0.jsonl`, `data/*.l0.json`
  only in a01). Feeds fork adjudication, not cards directly.
- **ARGMAP** — whole-verse argument (`ARGMAP.md`). All 22 present.
  Context for confirmations, never rendered.
- **L1** — controlled text (`L1.md`). All 22 present. Reference only.
- **L2** — plain-English exact meaning (`L2.md`). All 22 present.
  Fallback final where L3 absent (unused by cards today — flagged).
- **C1** — poetic essence (`c1/`). Present. Never rendered; taste lives here.
- **L3** — canonical translation (`data/tsa-aNN.l3.json`). ONLY a01 (5
  verses, needs human review). Verse finals prefer L3 when present.
- **L4** — the song (L3 set to music). NOWHERE yet — still ongoing.
  Cards prefer `l4` over `final` per entry the moment one lands, so the
  upgrade is a data fill, never a code change.

## Card layers (this repo)

Per Sanskrit display, top to bottom, closest to furthest:

1. **Deva** (ink 84) — glossary citation `deva`, never the folded key
   (M15). Sheets and video share the rule.
2. **IAST** (lightest grey) — derived per card from the display Deva
   (or the author's own roman half where present, M4/M16). Same onset.
3. **Literal** (mid grey, square brackets) — T1-style morphemes. Video
   gates on its own `literal_status`; sheets show proposed for review.
4. **Final** (darkest grey) — confirmed English gloss (terms) or L4-else-L3
   (verses, parked) — video gates on confirmed status throughout.

## Per-chapter layer status

- ch01: T1+L3 present; 16/16 terms confirmed; 16 literals proposed;
  3 verse entries proposed (parked).
- ch02–22: T1 present; L3 absent (a01 only); L4 absent everywhere.
  Bulk-confirmed 2026-11-04 (1368/1447; 79 uncertain held proposed —
  cards stay white there). Verse entries proposed where chants
  matched, else Deva+IAST automatic.
- Thumbnails: ch01 rainbow only; ch02+ fall back (wrong art, flagged).

## Autonomy contract

I work autonomously on everything the gates decide: rebuilds, mining,
sheets, segments, proof renders, gate runs, notes, docs, commits. I stop
and ask only where the law says an owner decides: casting marks, glossary
and literal confirmations, approvals, art, L3/L4 signoff, final ears.
Blocked inputs I cannot create: per-chapter thumbnails, free-tier quota
beyond tracking, local disk. Everything else, I do, prove, and log.
