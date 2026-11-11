# ChatGPT plugin: drive the video factory over MCP

Connect once, then run the whole factory: gate checks, triage, seamless
renders, publishing. This doc is the complete handover — read it, then work.

## Connect (custom connector, streamable HTTP)

URL: `https://vfshastra.loca.lt/mcp`

Add as a custom connector in ChatGPT (Settings → Connectors → Add custom).
No auth token today — the link itself is the secret. Transport: HTTP
(streamable). If the URL ever goes dark, the name is re-registered by the
`tunnel` service on the box; ask the owner for the current one
(`cat /tmp/lt.url.log` on the server prints it).

## The loop

1. `vf_status` — board state, locks, disk. Start every session here.
2. `vf_triage(project, unit)` — tells you what to do: gate verdict, per
   issue skill routing, recommended next step. Follow it.
3. `vf_gate` — the ONLY render gate: storyboard green + owner approval.
   Nothing else gates. Respect `vf_launch` refusals; use `vf_queue` when
   the video path is busy (it waits without sleep-blocking you).
4. `vf_skill(kind)` — full fix prescription per issue kind. `auto: true`
   skills you may apply unsupervised; `needs_owner` ones you file and stop.
5. `vf_seamless_draw` — the visual renderer: pen draws the exact opening
   frame (peak rule), hard cut, motion at speed/ramp, slow white fade.
   Byte-verified or fails loud. `recipe=` saves locked params+SHAs;
   `vf_seamless_cook` replays byte-for-byte.
6. `vf_publish` — R2 upload with byte-verify; returns the public URL only
   on match. `factory/` prefix for packs, lane prefixes for content.
7. `vf_check` — canonical gate must read CANONICAL before any render
   work you do ships. If it fails, fix what it names first.

## All 29 tools

Sense (read-only): vf_projects, vf_status, vf_units, vf_unit, vf_issues,
vf_gate, vf_logs, vf_finals, vf_catalog, vf_motion, vf_check, vf_tests,
vf_skills, vf_skill, vf_speakcheck, vf_passage_plan, vf_shorts_mine,
vf_roady_pack, vf_seamless_recipes, vf_registry_resource,
vf_visuals_resource, vf_gate_resource.
Decide: vf_triage.
Act: vf_launch, vf_queue, vf_pack, vf_publish, vf_skill_propose,
vf_speakclean, vf_seamless_draw, vf_seamless_cook, vf_approve_pack.

## File map (to edit and rebuild this plugin)

- `vf_mcp_server.py` — every tool lives here. Add a tool = one
  `@mcp.tool()` async function returning a JSON string
  (`json.dumps(await _run_sync(_work))`); pure helper above it, tested in
  `tests/test_mcp.py` or a new `tests/test_*.py`.
- `core/skills/<kind>.md` + `core/skills/REGISTRY.json` — fix
  prescriptions (`vf_skill_propose` stages them; commit separately).
- `core/builders/` — render pipeline (single copy; lanes never fork).
- `core/art_bank/motion/` + `motion.json` — GIF bank (slugs only).
- `projects/*/` — lane plugins (match/unit/paths; engine stays generic).
- `ops/pack_mcp.py --upload` — rebuilds the R2 pack outsiders use.
- Systemd: `vf-mcp.service` (server :8930), `vf-mcp-tunnel.service`
  (public URL + allowlist maintenance via `ops/mcp_public.sh`).

## Monitoring to script

- Daily: `vf_status` (locks, disk, builders) + `vf_check` canonical.
- 6-hourly during renders: `vf_gate` per active unit + `vf_logs`.
- Weekly: failure-class review — group recent `vf_issues` kinds; a new
  repeating kind becomes a skill (research → draft → test → commit with
  the fix, per the flow law in `core/skills/REGISTRY.json`).

## Auth plan (do before sharing widely)

Today: none — anyone with the URL can call all tools including
`vf_launch` (gated) and `vf_publish`. Acceptable for a private link.
Before any wider sharing: put a shared token in `Authorization` (add a
middleware check in `vf_mcp_server.py`, ~20 lines) or front it with
Cloudflare Access; rotate the tunnel name at the same time.

## Laws that do not bend

Storyboard green + owner approval gates every render. One video build at
a time. Free voices only. White law, 5-minute cap, byte-identical seams.
You never approve, waive, or bless — those are owner acts; file and stop.
