# UNITS — series unit conventions (owner-set 2026-11-05)

A unit is one renderable, shippable film: one storyboard, one glossary,
one approval, one mp4. Tantrasara units are chapters (22). Shiva units are
sutras (78). Future series choose their own units by the rules below.

## Sizing (guidance, not law)

- Target ~10 units per series. Smaller than 3 is a short; larger than 20
  needs a bland reason (shiva's 78 are one-per-sutra by the text's own
  structure — that reason counts).
- A unit should render to roughly one sitting: 5–60 minutes. Over ~90
  minutes, split by the text's own joints (books, sections, dialogues),
  never mid-argument.
- Unit count is set once at intake (owner call) and recorded in the lane
  INTAKE file. Changing it later re-blesses everything downstream.

## When the source has no chapters: manual creation

If the work arrives as one dump, a lecture series, or scattered texts,
the agent defines units manually — same discipline as a split, without a
splitter:

1. Read the whole thing first (no shortcuts). Grasp note: arc + threads
   that must survive (tantrasara BUILD-NOTES §5 pattern).
2. Cut by the argument, not by length: each unit gets one question or one
   movement (VISION §3 pattern: six questions for 22 chapters). One idea
   per unit, ink on white.
3. One file per unit: `chapters/uNN-slug.md` (or lane equivalent) in the
   chapter-file shape — H1 title, `##` sections, verses, dialogue in
   quotes, provenance tails — so every downstream builder works unchanged.
   Never prose of your own (R1): arrange the author's words, bridge with
   nothing.
4. Intro/outro per unit follow CHAPTER-FORMAT beats (bell → title+role →
   overview → handoff → verse → body → outro); the handoff line is the
   author's own words from the text, never composed.
5. Filler check: each unit must earn its thumbnail (a verse anchor + at
   least one term worth carding). A unit with no chant and no terms is a
   section of its neighbor, not a unit — merge it.
6. Intake log records: unit list + why-each (one line each), word counts,
   verse counts, open questions for the owner. Then the normal chain
   (storyboard → gates → sheets → publish → approval) takes over.

## Naming

Units sort by zero-padded number (`u01`… or lane scheme like `s00`…`s77`,
`ch01`…`ch22`). Storyboard/glossary/drops/review keys derive from the
unit id in exactly one place per lane (M30). Legacy quirks (ch06 `ch6`
stem) are documented in the lane config, never re-derived per script.
