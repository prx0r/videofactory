# Visuals — house law for every lane (owner orders 2026-11-08)

## Priority ladder (storyboard visuals resolve top-down)
1. **Devanagari + English gloss.** Where the lane carries Sanskrit, verse
   and term cards fire first on confirmed glossary. Nothing outranks the
   text itself.
2. **GIF motifs — must repeat.** A moving emblem is earned only by
   recurrence across beats or units (dog, whirlpool, lamp). One-off
   images never become GIFs; they stay draws or nothing.
3. **Drawn seals — best for long passages.** One per flagged gap, filed
   only after scan + audit (BUG→engine, honest white→draw). The ideal is
   a LANDSCAPE relevant to what's being said (strait swirls for the
   whirlpool, dawn beach for remembrance), never decoration.

## GIF thesis
Repeating motifs graduate to motion for dwelling; draws stay pacing
filler. Bank at lane `process/image-bank/motion/<slug>.gif`; first frame
doubles as the still until motion support lands. Spec: GIF89a loop, ~12
frames, ~310x414 or square, 0.5–1.5 MB, white ground, blue-ink
pencil-engraving line, minimal, no text, seamless loop, one moving
element. Full maker sheet lives wherever GIFs are made; this is the law.

## Draw thesis
Small centered emblem, generous white margin, subtitle-safe. Prefer
isolated-on-white or transparent sources; dark full-bleed photos need
re-grade or rejection (record the call). Public-domain and museum
open-access (MET CC0, Wellcome CC-BY with attribute) outrank stock;
stock under free license with provenance logged. Paid generation needs
explicit confirm. Proposed draws never render — owner promotes per gap
with a why, filed as `draws_<stem>.json`.

## White law
Emblems float on white like thumbnails. Lane banks carry an executable
rim check (mean > 225); anything else fails loudly.

## Five-minute cap (owner law 2026-11-11)

No single visual holds longer than ~300 seconds. Gaps over 180s already
split into ~90s sub-draws; anything that would still hold past five minutes
splits into movements (etch → motion → breath → next), each with its own
art and its own why. Long single-block narration splits at render time on
measured onsets. `vf_seamless_draw` refuses segments over 300s — split
the passage instead.

## B-roll (full-bleed scenery)

Forest waters, night streets, open seas: B-roll breaks the white law on
purpose and plays FULLSCREEN (`fullscreen: true` on the clip), never the
mini canvas. Bank entries carry `"broll": true`. Karaoke continues over
it; slow fades in and out. Sparingly — a break, never wallpaper.

## Lane notes
- nibbana: no-Pali, so ladder starts at 2 (draws/GIFs carry the lane).
- paramarthasara: mirror is the lane mark; parts take their own seals.
- shiva-sutras: fire first (27x), then seed, ocean, wheel.
- tibetan-dead: mandala banked for the deity days; death bell at opens.
- deathworks: anubis + tombstone banked; phowa ejection diagram banked.
