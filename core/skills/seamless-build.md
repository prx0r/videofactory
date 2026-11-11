# seamless-build (the one visual system: etch, play, fade)

There are no separate GIFs and draws. There is one thing: the pen draws
the exact opening frame for as long as the passage needs, the GIF plays,
the white takes it back. Everything below is that thing.

## The shape

1. **Etch** — skeleton pen paths, bottom-up bands with breaths (techdou
   walk order), native size, centered on pure-white 1920x1080, never
   rescaled. Length is free: 30 seconds for a beat, 3 minutes for a
   buildup — the etch just slows. Ink first (sketch), grain after (colour),
   so the arrays match exactly at completion with no end jump.
2. **Cut, never fade in** — final etch frame and first motion frame must
   be byte-identical at identical placement (verify with np.array_equal).
   A size or position jump between etch and motion is a defect: re-file
   the etch, never ship it.
3. **Play** — 2x ~20s default. The motion is baked player-agnostic; speed
   lives in the render, not the file.
4. **Fade** — slow dissolve to white (3.5s default) while karaoke
   continues; durations unchanged.

## Passage timing (preferred over fixed lengths)

Pass `storyboard` + `from_bid` + `to_bid`: the tool estimates the spoken
span (visual-plan durations where pinned, else words/granny-wps) and splits
it — etch across the buildup (~65%), motion over the tail and beyond.
The etch completes on the payoff beat (the dog shouts, the knot breaks),
not on a keyword. Fixed `etch_s`/`play_s` is for demos only.

## Speed ramps (the speedup recipe shape)

`ramp=0.25,0.5,1,2,4` plays the loop once per speed step, each step an
equal share of `play_s`: crawl, walk, run, fly. `direction` reverses or
pingpongs the frame order. Name any combination with `recipe=` — params,
input/output SHAs, env versions — and `vf_seamless_cook` replays it
byte-for-byte (`replay_match=true` proves the lock).

## Running it

- `vf_seamless_draw(gif_id, unit, ...)` — renders to `~/vol/<lane>/`,
  verifies seam + placement, optionally publishes. Fails loud on any
  mismatch (unknown gif, bad ramp, seam cut mismatch, ffmpeg fail).
- `vf_seamless_recipes` — lists saved recipes with SHAs.
- `vf_seamless_cook(recipe, gif_id, unit)` — exact replay + byte-match
  report. New GIF, same recipe: same shape, new subject.

## Filing it into a lane

A render is a demo until filed. Suggested lane entries come back in
`passage_plan.suggested`: draw {start: from_bid, complete: mid_bid} with
the first-frame still as asset, clip {start: mid_bid, ...} with the baked
motion. File as `draws_<stem>.json` / `clips_<stem>.json` beside the drops,
re-validate with `draws_for`/`clips_for`, and the unit is ready to insert.
