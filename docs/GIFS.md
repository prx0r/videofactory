# GIFs — house motion emblems (maker sheet)

Doctrine, mechanism, and technical reference live here; lane queues live
in lane logs. Companion to docs/VISUALS.md (priority ladder: GIFs are
earned by recurrence; draws are pacing filler).
Skills: gif-choose (pick), gif-request (order), seamless-build (render).

## One visual system (owner law 2026-11-11)

GIF and draw are the same thing: the pen draws the EXACT opening frame
for as long as the passage needs (30 seconds or 3 minutes — the etch just
slows), then the GIF plays with a hard cut, then a slow white fade. Etch
length is passage-timed, never hardcoded; motion runs 2x ~20s unless a
ramp says otherwise (0.25→0.5→1→2→4 is the speedup recipe shape).
vf_seamless_draw renders it, recipes replay it byte-for-byte.

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

## Etch-to-GIF seamlessness (owner law 2026-11-11)
The etch subject must BE the clip's opening frame — the pen draws the
exact image the GIF starts on, never a resized or reinterpreted cousin.
Final etch frame and first clip frame must be byte-identical at identical
placement: native GIF size, centered on pure-white 1920x1080, no rescaling
anywhere in the chain (no crop_169, no canvas refit). Bank GIFs carry a
paper veil (backgrounds ~241-252, never pure white — audited across the
bank 2026-11-11), so backgrounds at or above 250 are lifted to 255 first;
the canonical bank stays untouched and the cleaned frame is the verified
subject. Pen order follows
skeleton paths bottom-up in bands with breaths (techdou walk), ink first
then shading and paper grain along the same paths (sketch-then-color, no
end jump); the arrays match exactly at completion. Verify
before any publish:

python3 -c "import numpy as np; from PIL import Image;
e=np.asarray(Image.open('etch_final.png')); m=np.asarray(Image.open('gif_first_placed.png'));
assert e.shape==m.shape==(1080,1920,3); assert np.array_equal(e,m)"

A jump in size or position between etch and motion is a defect — re-file
the etch, never ship it. The etched subject defaults to the opening frame;
fade-in-style loops that open on blank use the peak (fullest) frame with
playback rotated to start there — same byte-identical seam either way.
The reveal itself is verified drawn, not wiped: per-band reveal-rank vs
height correlation must stay under 0.9 (wipes score ~1.0), or the render
refuses.
