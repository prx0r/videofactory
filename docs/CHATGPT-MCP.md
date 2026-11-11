# ChatGPT handover: run the whole factory from MCP

Goal: ChatGPT (or any agent) with this repo, R2 access and server2 access
drives any unit from storyboard to shipped final through MCP tools alone —
validate, voice with Fish, assemble, check, publish — using the GIF bank,
B-roll stocks, and the seamless renderer, and grows the collection itself.

## What already works (do not rebuild)

- Board: `vf_status`, `vf_units`, `vf_catalog`, `vf_finals`, `vf_projects`.
- Gates: `vf_gate`, `vf_triage`, `vf_check`, `vf_tests`, `vf_issues`,
  `vf_skill`, `vf_skills` (22 skills incl. gif-choose/gif-request/
  seamless-build/markdown-speech).
- Visuals: `vf_motion` (tags filter), `vf_seamless_draw` (etch→play→fade,
  passage mode, ramps, recipes), `vf_seamless_recipes`, `vf_seamless_cook`
  (byte-match replay), `vf_passage_plan`, `vf_approve_pack`,
  `vf_speakcheck`, `vf_speakclean`, `vf_shorts_mine`, `vf_roady_pack`.
- Render: `vf_launch`, `vf_queue` (gated), `vf_pack`, `vf_publish` (R2,
  byte-verified).
- Lane work staged: 63 units across nibbana/paramarthasara/paratrishika/
  tibetan-dead/deathworks carry draws+clips+thumbs+sheets+issues+pending
  manifests (in their repos, uncommitted — commit per lane on owner go).
- R2 pack (`factory/` prefix): whole MCP as a zip + manifest for outsiders.

## What ChatGPT builds (this PR is the scaffold)

1. `vf_gif_submit` — intake tool: takes a GIF file + motif/brief, runs the
   arrival checklist (12 frames, even delays, white rim, seamless loop,
   byte-dupe check), files it under its slug, flips the registry entry
   with depicts/means/use/watch. Refuses with reasons; never silently banks.
2. `vf_stock` — unified B-roll search/fetch: Pixabay (key in env) +
   Wikimedia Commons (keyless) + Internet Archive via broll-mcp. Search,
   download, transcode to mp4, contact sheet, provenance + license record
   (CC attribution is REQUIRED — unlike Pixabay), draft registry only.
   Owner approves before anything banks. See `ops/fetch_commons.py` (saved
   working process) for the Commons half.
3. Fish TTS wiring — no code: builders already call Fish per audio group.
   Needs `FISH_API_KEY` in server2 env (owner provides; `preflight.py`
   checks it). Document the exact placement + a preflight run.
4. Passage auto-plan at lane scale — run `vf_passage_plan` over every
   pending manifest, file suggested draw/clip entries, validate.
5. Approval packs — `vf_approve_pack` per unit, owner reviews once,
   blesses (blanket or per-unit), waivers for the 14 para verse warnings.
6. End-to-end acceptance — one pilot unit (nibbana n02 suggested: dog
   passage recipe exists): audio on server2 → video build under the
   one-video lock → `vf_pack`/`vf_publish` → R2 pack refresh (`factory/`).

## Secrets (owner provides, never in repo)

- `FISH_API_KEY` → server2 env (audio renders only run there).
- `PIXABAY_KEY` → hub `~/.config/easy/pixabay.env` (already placed).
- R2 creds → rclone `r2` remote (already placed, both boxes).
- Cloudflare (sleepdraw FLUX) → server2 `/root/.r2-env` (paid seals only).

## Laws that do not bend

Storyboard green + owner approval is the only render gate. One video
build at a time. Free Fish voices only. White law + 5-minute cap +
byte-identical seams (refuse, never fudge). Reads before writes;
no owner-only acts, ever.
