# HANDOVER — read this first (written 2026-11-08, evening)

New agent: this file is the whole state. Read it, then start at
"Do next". Do not re-ask anything under "Standing orders".

## Do next (in order)
1. **s29** — owner picks one of the 4 options below, then execute.
2. **Mega + Book I** — concat on server2 once s29 ships (commands below).
3. **Shorts output** — voice granny shorts, handcraft Roady ones, render
   verticals on server2, upload to `r2:svread-audio/shorts/`.
4. **GIF queue** — press ChatGPT in this priority: shiva seal four
   (fire/seed/ocean/wheel) → paratrishika (trident/bee/knot) → nibbana
   (surgeon n01, signpost n01, grasping-hand lane-wide, leaning-wall n02)
   → roady-first set (fifa-night + 7 unassigned London motifs).
5. **Draws** — per-lane visual plans exist; render FLUX stills on server2.
6. **Uploads** — every publish = rclone copyto + lsl + HEAD match.

## Lane states (exact)
- **shiva-sutras** (`/home/ubuntu/shiva-sutras`, frozen): 77/78 finals.
  `r2:svread-audio/shiva/` has s00-s28 + s30-s77 `_full.mp4`; s29 missing.
  Public base: `https://pub-87169194562a44fcb8279a799d626c62.r2.dev`.
  Outstanding: ears + seals + GIF mapping (fire/seed/ocean/wheel, units
  TBD at seal stage).
- **tantrasara** (`/home/ubuntu/tantrasara`, frozen): 22 shipped-shape.
  Outstanding: heart-flame GIF (ch13, wanted), seal-stage GIF mapping.
- **nibbana** (`/home/ubuntu/nibbana`): 10 green boards (n01-n10);
  `process/visual-plan.md` = GIFs + 60-120s draw per unit; drops wired
  (R-G/S-G prefixes); pack: `vf_nibbana_pack`. Renders blocked on
  shared-code debt (see below).
- **paramarthasara** (`/home/ubuntu/paramarthasara`): 7 green boards;
  visual plan done; GIFs: crystal p01, rice p02, spiderweb p03,
  sunrise-water p04, doorway p05, skullbowl+tombstone p06, dawn p07.
- **tibetan-dead** (`/home/ubuntu/tibetan-dead`): 5 green boards + d-before
  (accounting policy P0); visual plan done (scroll d01/d02, lamps d01,
  prayer d-before, rainbow d05, toll d01, mandala+scales d02).
- **deathworks** (`/home/ubuntu/deathworks`): 5 green boards
  (heist/escape/rebirth/madman/ancestors, all sections green); visual
  plan done (phowa-pin, anubis x2, prayer ancestors).
- **paratrishika** (`/home/ubuntu/paratrishika`): 36 green boards v01-v36;
  visual plan done (mostly letter-seal draws); 92 letter-seals: beej + 70
  + 75 committed, +PDF75 (MathML, owner CONFIRMED); 16 sound-change seals
  PENDING owner choice (aYE/ayaYE/aiYE × 4 spellings) — do not render.
- **shorts** (`videofactory/projects/shorts/`): 54 units (50 granny +
  receipt/roady pilots + handoff + white loop); index + no-repeat law in
  `projects/shorts/index.json`; recipes in `projects/shorts/ROADMAN-RECIPE.md`;
  Big G + Roady voices live; roadman seat wired (frozen-proof passed);
  pilots rendered; `granny-hamlet.wav` uploaded
  (`.../shorts/granny-hamlet.wav`, 3554974 bytes).
- **GIF bank** (`core/art_bank/motion.json`): 87 entries, 36
  banked-described (all with depicts/means/use/watch/used_in), 49 wanted
  + 2 in flight. Files in `core/art_bank/motion/`.

## s29 BLOCKED (3 attempts, deterministic)
`RuntimeError: MMS cannot align 8 words (17aaa) after retries`. NOT a
flake: whisper hears the group audio byte-perfect, specs match working
neighbors, a fresh TTS take fails identically. Group 17 = block b69
(granny): "These are connected with further differentiations involving
the powers and their relations to elemental principles."
Aligner: node `core/builders/align_group.js` (NODE_PATH=/tmp/mmsmod).
Repro: `node core/builders/align_group.js <wav> <words.json> <out> en`.
Owner picks: (a) isolate choking word(s) via manual runs; (b) reword b69
then rebuild+requeue; (c) speed-0.9 group render into the hash slot;
(d) scholar review. NEVER edit shared align code without frozen-proof.

## Mega + Book I (wait on s29, run on server2 `root@2.28.50.109`)
- Mega s00-s77 concat of R2 finals; Book I = s00-s22 cut.
- Trim audio to video duration (av-sync ≤10ms), ffprobe verify, rclone
  to `r2:svread-audio/shiva/`, lsl + HEAD Content-Length match, return links.

## Render debt (before nibbana/param/tibetan/deathworks/para render)
Shared code assumes shiva paths: gate lane-awareness, holds.lane_for
routing (hold specs live in lane repos), render-path parametrization.
Fix behind frozen-proof (validation embedded in builders) or keep lanes
in prelim until owner says otherwise.

## Standing orders (do not re-ask)
Render gate = storyboard green + owner approval only. One video build at
a time. Rule 8: ffmpeg on the render box, never the hub (ffprobe ok).
Free Fish voices only. No-Pali (nibbana). Sanskrit-only, no Tibetan
(trilogy/deathworks). White-law emblems on everything. R2 publish =
copyto + lsl + HEAD. ChatGPT owns the GIF queue; bank arrivals with
depicts/means/use/watch + unit slots. FLUX stills on server2
(`/tmp/sdeng`, creds `/root/.r2-env`); etch only on order.
