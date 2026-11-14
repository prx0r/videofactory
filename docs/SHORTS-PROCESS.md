# SHORTS PROCESS — from long-form to verticals (2026-11-14)

Canonical workflow for turning finished long-form into shorts. Sources of
truth: `docs/SHORTS.md` (format/rubric), `core/skills/granny-distill.md`,
`core/skills/roadman-shorts.md`, `projects/shorts/ROADMAN-RECIPE.md`,
`projects/shorts/index.json` (54 units, uniqueness law).

## Thesis
A short is a re-cut, never a re-render. Audio = verbatim slices from the
content-hash group wavs. Pictures = GIF/draw bank. No new recording.

## Format (hardcoded)
1080x1920 9:16, 30fps, H.264 + AAC stereo, ~8 Mbps, target 60s (ceiling 3 min,
never the target). Safe zone top 288 / bottom 672 / left 48 / right 192;
emblem ≤440w centered ~y690-960; voice tag y620; captions from y1210; hook
y680-750; first frame on the subject; A/V ≤10ms (atrim-exact, av-sync law).
First frame starts on the subject.

## Two formats
1. **Granny minute** (`granny-distill`): 45–60s (~140 words) that passes the
   LIBERATION TEST — "would this change what someone does tomorrow?" Mechanisms
   pass, definitions fail. Mine long-form for mechanisms, condense verbatim,
   keep one joke, cut decorators. Every line maps_to source bids.
2. **Roady G** (`roadman-shorts`): Roady reacts to the GIF live, talking to his
   mate. Modes by topic: ramble (dwelling images), quickfire (processions/lists),
   mixed. Hook-first cold open on the punch. GIF AS BIG AS POSSIBLE, always about
   the picture, new GIF pops BEFORE talk, made-up words + true doctrine, close on
   the mutter. Register bans cap/fr/bussin/vibe/delulu/lowkey.
   - **Derivation formula (granny + GIF + graph = bit):** take granny's 60s +
     its GIF → pick one house SO + one LM from
     `core/knowledge/comedy-graph.json` that the minute already contains →
     cast Roady from `core/knowledge/roady-profile.json` → CHECK triple
     (SO+LM+situation) against the graph (collision = rewrite) → close on mutter.
   - **Roady-first:** Roady opens everyday, Big G answers straight, Roady refuses
     the teaching — the refusal is the punchline.

## Voices
- Granny = house granny seat. Roadman = `e64e97ef91304e2894cd72ff03b86d97` on
  `fish-audio/s2.1-pro-free` (free-only law). Verse/narration stay house voices.
  Candidate status until ears bless.

## Tools (MCP + CLI)
- `vf_shorts_mine(project, unit)` — score candidate spans (exchanges, verse+
  gloss, caps rants, openers/closers) per lane.
- `vf_roady_pack(short)` — derivation packet: granny lines + GIF options + SO/LM
  triples + register (the creative reword stays human/agent-side).
- `vf_motion(status, lane, query)` — GIF bank lookup (173 entries).
- `vf_skills` — roadman-shorts / granny-distill / gif-choose / seamless-build.

## Render path (per ROADMAN-RECIPE)
1. Storyboard JSON in `projects/shorts/storyboards/shorts_*.json` with `directed`
   (roadman reword), `maps_to` source bids (C2 rule), `voice: roadman`.
2. One Fish TTS call per line → `lNN.wav` (receipts logged).
3. Stitch in plain code, INTEGER frame math only: `gap = rate*ch*sw*35//100`
   (~0.35s breaths). Float seconds corrupt the tail.
4. Verify: total bytes even, header==data size, clean full decode.
5. Video (server2, Rule 8): vertical cards per line → per-line mp4 →
   `concat -c copy` → atrim-exact audio to video (≤10ms) → verify → publish.
6. Publish: `rclone copyto` + `lsl` size match + HEAD Content-Length.

## Uniqueness law (index.json)
No two shorts share a source span; emblem reuse only on motif match. New short
checks the index first. File every aired bit back to the comedy graph.

## Known state (2026-11-14)
- 54 units: 53 `storyboard`, 1 `rendered+R2`.
- **Dependency to solve before mass shorts:** shorts slice the group-wav cache,
  but the audio-only pass publishes mp3 and deletes the wav cache. Decide:
  retain per-lane group wavs (disk) or re-render audio per short batch.
- Roady register/mode judged by ear (needs owner).
