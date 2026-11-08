# Handover — next session (written 2026-11-08)

## Continue from here
1. **Shorts output.** 54 storyboarded (50 granny + receipt/roady pilots +
   handoff + white loop), index + no-repeat law at
   `projects/shorts/index.json`. Next: voice more granny shorts (recipe
   in `projects/shorts/ROADMAN-RECIPE.md`), handcraft Roady versions one
   at a time (pack via `vf_roady_pack`, skill `roadman-shorts`), render
   verticals (pilot pattern on server2), upload to `r2:svread-audio/shorts/`.
2. **Uploads.** Long videos + shorts to publish; verify lsl + HEAD each.
3. **GIFs in.** Motion bank `core/art_bank/motion.json` (66 entries:
   29 banked, 37 wanted). ChatGPT works the wanted queue; flip to
   banked-described with depicts/means/use on arrival.
4. **Drawn stuff.** House prompt at `core/art_bank/draw-prompt.md`;
   FLUX stills render on server2 (`/tmp/sdeng` engine + `/root/.r2-env`
   creds); etch only on order. Letter-seals typeset locally (no garble).

## Lane states
- shiva-sutras: 77/78 finals (s29 BLOCKED, see below). Ears/seals outstanding.
- tantrasara: frozen, 22 shipped-shape.
- nibbana/paramarthasara/tibetan-dead/deathworks/paratrishika: prelim
  complete (green boards, casting sheets, glossaries, drops, packs).
  Shared-code debt before any render: gate lane-awareness,
  holds.lane_for routing, render-path parametrization.
- shorts: 54 units, pilots rendered (receipt, dawn handoff), Big G +
  Roady voices live, roadman seat wired (frozen-proof passed).

## s29 (BLOCKED, 3 attempts)
`MMS cannot align 8 words (17aaa)` — deterministic, NOT flake/mount/
take-specific. Group 17 = single block b69 (granny, plain English,
whisper-verified byte-correct, specs identical to neighbors, fresh TTS
take fails identically). Aligner: node `core/builders/align_group.js`
(NODE_PATH=/tmp/mmsmod). Repro:
`node core/builders/align_group.js <g017.wav> <words.json> <out> <lang>`.
Options (owner picks): isolate the choking word(s) via manual runs;
reword b69 (prose edit, then rebuild+requeue); speed-variant group
render (0.9) into the content-hash slot; or scholar review. Do NOT
touch shared align code without frozen-proof (validation is embedded).

## Standing owner orders (do not re-ask)
Render gate = storyboard green + approval. Rule 8: ffmpeg on render
box, never hub (ffprobe ok). Free Fish only. No-Pali (nibbana),
Sanskrit-only-no-Tibetan (trilogy/deathworks). White-law emblems.
Mega + Book I concat wait on s29. R2 publish = copyto + lsl + HEAD.
