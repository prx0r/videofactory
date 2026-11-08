# GIFs — house motion emblems (maker sheet)

Doctrine, mechanism, and technical reference live here; lane queues live
in lane logs. Companion to docs/VISUALS.md (priority ladder: GIFs are
earned by recurrence; draws are pacing filler).

## Where things live
- Canonical bank: `core/art_bank/motion/*.gif` + `core/art_bank/motion.json`
  (id, motif, file, used_in per lane, status banked/wanted).
- Lane caches (e.g. nibbana `process/image-bank/motion/`) are working
  copies; canonical wins on conflict.
- Review surface: contact strips beside the bank.

## Maker envelope (match the banked set)
GIF89a loop, ~12 frames, ~310x414 portrait or square, 0.5–1.5 MB, white
ground, blue-ink pencil-engraving line, minimal, arty, NO text, seamless
loop (last frame flows into first). One moving element, rest still.
Slugs lowercase-hyphenated (`fire-out.gif`). New GIFs land here first,
lane caches second.

## Playback direction (render-time, baked to mp4)
Speed and direction are render decisions, not file properties: 2x halves
frame delays, 0.25x quadruples them (`setpts`), reverse runs `-vf
reverse`. Even-delay loops retime cleanly; uneven ones judder. Slow
passes strobe by design (steppy-meditative). White holds append after
the last pass. Ritual example (om-reveal): nine passes at 2x, one final
pass at quarter speed, three seconds of white — 27.5 seconds total,
fit for closings and openings, never mid-beat. Direction lives on the
registry entry; render reads it.
