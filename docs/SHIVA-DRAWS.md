# Shiva draws — spec + candidate queue (owner-ordered, 2026-11-06)

Owner calls: (1) the s00 Kashmir intro IS a draw — mountains of Kashmir,
Vasugupta, the rock; (2) no draws filed yet — spec them, find the
similar long-narrative moments, file later with art. This doc is that
spec. No draws_chNN.json is filed until the image assets exist
(`draws_for` fails closed on missing assets — a spec without art stays
a spec, never a half-render).

## Draw 1 (spec'd, awaiting asset): s00 Kashmir establishing panorama

- **span**: start_bid `b4` ("Right. We're back in Kashmir." — scene is
  established, fade in from the white hold), complete_bid `b8`
  ("Seventy-seven tiny statements." — mountains + Vasugupta + dream +
  rock + revelation all spoken).
- **hold**: persist through the overview (s00 has no cues/chants/breaks;
  the 95s white gap at b1 is exactly this span) until the unit ends;
  clear `fade` 2.0s into the handoff (`b17` "Lets get into it").
- **why**: the series establishing shot — the only landscape in all
  78 units; everything else plays over white by design.
- **final image spec** (for the artist/model; muted nocturnal palette
  matching the series line-art, ink-on-white DNA, never photoreal):
  night Himalayas, snow ridges under a thin moon; a small ancient stone
  temple half-buried in snow mid-ground; in the foreground a mossy rock
  face with faint carved syllables catching moonlight; a lone sleeping
  figure (Vasugupta) wrapped in a blanket before it, dreaming; no faces
  in detail, no text in the image, no borders — full-bleed art fitted
  inside the safe zone (85px margins, above y=860), composed so the
  heaviest ink sits center/upper (subtitle zone stays clean).
- **file when art lands**: `shiva/draws_s00.json`:
  `{"b4": {"asset": <path>, "complete_bid": "b8", "clear": "fade",
  "fade": 2.0, "why": <above>}}` — then re-render s00 parts + re-prove.

## Candidate queue: longest white holds (draw-shaped moments)

Ranked by span; `proposed` = the gap holds a proposed-term chant (confirm
the term first OR draw for pacing — owner call per span); `clean` = pure
exposition, ideal draw material; `recap` = cross-unit repeat (reblock
decision first, see stale-verse-hold).

| span | unit | block | kind |
|---|---|---|---|
| 283s | s25 | b24 | proposed-term gap |
| 259s | s54 | b15 | proposed (`samadarsanam`) |
| 252s | s70 | b43 | proposed (`srsti`) |
| 246s | s40 | b2 | exposition open |
| 245s | s22 | b24 | proposed (`matrka`) |
| 228s | s37 | b20 | exposition |
| 222s | s32 | b22 | recap run (reblock first) |
| 217s | s48 | b14 | exposition |
| 207s | s31 | b31 | exposition |
| 203s | s66 | b39 | exposition |
| 202s | s28 | b2 | exposition open |
| 201s | s57 | b28 | proposed (`turyatita`) |
| 198s | s55 | b28 | exposition |
| 197s | s61 | b37 | exposition |

Full list: every `white-gap`/`stuck-term` issue in
`~/vol/shiva/renders/issues/sNN.issues.json` (record-only by design;
draws filed per span only with art + owner why, never in bulk).

## Rules for filing (same as tantrasara sleepdraws)

Entry fades in from white between the two onsets; held complete until
the next cue/chant/tone-break (cues always win); clearing is fade or
cut per spec. Asset must exist before filing. One concern per commit.
Ears dispose: owner watches the span with the draw before seal.
