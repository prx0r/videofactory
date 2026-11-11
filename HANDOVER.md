# HANDOVER — read this first (rewritten 2026-11-11 evening session)

New agent: this file is the whole state. Read it, then start at
"Do next". Standing orders at the bottom still apply — do not re-ask them.

## Where everything stands

- **shiva-sutras + tantrasara: CLOSED by owner.** No further work in
  either lane. Shiva shipped 77/78 (s29 gap waived); tantra 22
  shipped-shape.
- **Focus lanes (pre-render staged, all pushed): nibbana (10),
  paramarthasara (7), paratrishika (36), tibetan-dead (5), deathworks
  (5).** Every unit carries: speak-clean boards, filed draws + clips
  (validated), per-unit thumbnails, contact sheets, issues files, pending
  manifests with passage timings, first-frames + 2x motion bakes.
- **GIF bank: 173 entries, 0 wanted, 18 spares.** Queue is CLEAR
  (heart-flame dropped by owner). 28 variants with when-rules, full-bleed
  scenic + forest B-roll sets marked (small-in-frame like everything —
  the fullscreen exception was built then fully reverted).
- **One visual system, locked:** etch the peak frame (never assume frame
  zero), hard cut, motion at speed/ramp, slow white fade. 5-minute cap
  enforced in code. Drawn-travel metric refuses wipes. Recipes replay
  byte-for-byte (`vf_seamless_cook` proved it).
- **Gates green:** `check.py` CANONICAL (215 passed, 1 env-skip that runs
  on server2). 49/63 bundles validate; 14 para units need owner waivers
  (drafts in `paratrishika/process/waiver-drafts.json`).
- **Para voice warning:** 28/36 units crash card rendering on Sanskrit
  verse-stack geometry (inventory in `paratrishika/process/
  sheet-failures.json`). Scholar restyle work — the one open content job.
- **Live remote MCP** for ChatGPT: `https://vfshastra.loca.lt/mcp`
  (systemd `vf-mcp.service` + `vf-mcp-tunnel.service`; see
  `docs/CHATGPT-PLUGIN.md`). R2 pack for outsiders under `factory/`.
- **B-roll stocks:** Pixabay key in `~/.config/easy/pixabay.env`;
  Wikimedia Commons via `ops/fetch_commons.py` (no key, CC attribution
  required); broll-mcp evaluated (wrong archive for our content).
  Stock registry draft: `core/art_bank/stock-pixabay.json` (owner has
  not approved any of it yet).
- **Open PR:** #2 `chatgpt-mcp-handover` (ChatGPT finishes: gif-submit +
  stock tools, Fish wiring, lane-scale filing, pilot end-to-end).

## Do next (rendering — needs owner + server2)

1. Owner approves 63 units (pilot per lane first: nibbana n02 suggested)
   + signs the 14 para waivers.
2. Audio renders on server2 (`FISH_API_KEY` in env; preflight checks it).
3. Video builds under the one-video lock, then ship + R2 pack refresh.
4. Para verse-stack restyle (scholar) unblocks its 28.

## Standing orders (do not re-ask)

Render gate = storyboard green + owner approval only. One video build at
a time. ffmpeg on the render box, never the hub (ffprobe ok). Free Fish
voices only. No-Pali (nibbana). Sanskrit-only, no Tibetan
(trilogy/deathworks). White law, 5-minute cap, byte-identical seams. R2
publish = copyto + lsl + HEAD. FLUX stills on server2 (`/tmp/sdeng`,
creds `/root/.r2-env`); etch only on order.
