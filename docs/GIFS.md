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
