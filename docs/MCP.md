# MCP control plane (videofactory MCP server, stdio)

`vf_mcp_server.py` is the agent-facing front door of the video factory. Any
MCP-capable agent — opencode, Claude, a headless driver — gets the same
twenty tools and three resources, over stdio, with factory law enforced
server-side instead of trusted client-side.

```
agent ──MCP stdio──▶ vf_mcp_server.py ──┬──▶ builders (gates, renders)
                                        ├──▶ artifacts (storyboards, finals, issues)
                                        └──▶ board (REGISTRY.json)
```

Reads never write. The five act tools (`vf_launch`, `vf_queue`, `vf_pack`,
`vf_publish`, `vf_skill_propose`) are the only writers, and each one
enforces the rule that covers it. Everything an agent needs to run the line
is here; everything that must stay human is absent (see §6).

## 1. Setup

opencode entry (global config `~/.config/opencode/opencode.jsonc`):

```json
"videofactory": {
  "type": "local",
  "command": ["python3", "/home/ubuntu/videofactory/vf_mcp_server.py"],
  "working_directory": "/home/ubuntu/videofactory",
  "enabled": true,
  "timeout": 180000
}
```

Notes:

- `command` is an array, `type` is required. Validate JSON before saving,
  keep `$schema`, then quit and restart opencode — config is not hot
  reloaded; the running session keeps the old set until restart.
- `timeout` 180s covers the slow tools (`vf_tests` full ≈ 95s, `vf_check`
  runs the whole unittest suite). The default 30s would kill them mid-run.
- The server needs the factory venv python only if builders need it; plain
  `python3` matches how the overnight supervisor runs.
- Name rule that cost us a red suite once: the file MUST stay
  `vf_mcp_server.py`. Bare `mcp_server` is sleepdraw's module name
  (`propose_draws.py` imports it); a root-level `mcp_server.py` shadows it
  and breaks bank tests. Lock test: `TestMcpServerNameLock`.

## 2. Concepts (read this once)

- **Lane**: a series (`tantrasara` — 22 chapters, `chNN`; `shiva-sutras` —
  78 units, `sNN`). `vf_projects` lists them; every other tool takes a lane.
- **Unit**: one renderable piece (`14`, `ch14`, `s24` all accepted — digits
  are normalized through the lane). Legacy split: ch06 storyboards use the
  `ch6` stem while finals/approvals say `ch06`; the server tries both digit
  variants everywhere, so agents never care.
- **Render gate** (owner order 2026-11-06): storyboard green + owner
  approval. It is the ONLY thing that can stop a render. Every downstream
  check is advisory/record-only. `vf_gate` evaluates it; `vf_launch` and
  `vf_queue` refuse without it, with the reason named.
- **One-video law**: one video build at a time (fixed `/tmp` paths +
  `/tmp/video_build.lock`). Launch refuses while builders run; queue waits.
- **Issues, not errors**: `check_issues.py` writes per-unit
  `issues/<stem>.issues.json`. Each issue has a kind, severity, status
  (`open` vs `waived-owner`), and a skill pointer. Open + record-only never
  blocks a render — it routes work.
- **Skills**: `core/skills/<kind>.md` fix prescriptions, indexed by
  `core/skills/REGISTRY.json` with `auto` (agent may apply unsupervised) vs
  `needs_owner` (agent stages, owner disposes). Flow law lives at the top of
  that REGISTRY file.

## 3. Tool reference

Calling convention: all tools return JSON strings. Errors are
`{"error": ...}` or `{"launched": false, "reason": ...}` — never an
exception, never silence.

### Sense

**`vf_projects()`** — lane discovery. Returns lanes with series, unit
count, id scheme. Call before anything when you don't know the factory.

**`vf_status()`** — the board snapshot. Gate mode, milestone table, locks,
live-builder count, vol/tmp free GB, tails of the overnight / batch / ch14
/ chain logs. Call first in every session: it tells you what is running,
whether the path is free, and whether disk is the problem.

**`vf_units(project)`** — whole-lane stage table derived from artifacts
(finals, approvals, issues). Stages: `approved-ready` (gated, unrendered),
`video-needs-review` (final exists, ears/seal outstanding), `needs-review`
(no approval yet), `missing-storyboard`. Example row:
`{"unit": "14", "stage": "approved-ready", "final": 0, "issues_open": 9}`.

**`vf_unit(project, unit)`** — deep state for one unit: storyboard path +
short sha, approval present, final bytes, open/waived counts, ship verdict,
parts-with-meta count.

**`vf_issues(project, unit)`** — the raw issues file. Each entry carries
`id`, `kind`, `severity`, `detail`, `blocks`, `skill`, `status`.

**`vf_gate(project, unit)`** — evaluates ONLY the render gate:
`storyboard_green`, `approved`, `may_render`. Example (ch14):
`{"storyboard_green": true, "approved": true, "may_render": true}`.
If `may_render` is false, stop — nothing downstream can help.

**`vf_logs(name, lines=40)`** — tails allowlisted `/tmp` logs (`batch`,
`overnight`, `batch_ch14_retry`, `chain_renders`, …). Names are allowlisted;
path traversal is refused.

**`vf_finals(project)`** — shipped mp4s with bytes, ship verdicts, and
public R2 URLs (`https://pub-…r2.dev/<lane>/<stem>_full.mp4`).

**`vf_catalog(project)`** — per-video catalog: display title (lane
convention from chapter source) + thumbnail (per-unit stem art or series
fallback) + state (storyboard sha, approval, stage, final bytes, issues,
ship) for every unit. Owners drop per-video art at
`assets/thumbnail/<stem>.png` and it appears here on the next run.

**`vf_check()`** — runs `check.py`; `{"canonical": true}` or the failing
tail. The factory definition of done for code changes.

**`vf_tests(scope="quick")`** — quick subset (draws/postmortem/ship,
seconds) or `full` (≈2 min). Must pass under the caller's timeout.

### Decide

**`vf_triage(project, unit)`** — the decision tool; start here whenever the
question is "what should I do about X?" Returns unit state + gate verdict +
every issue joined to its skill metadata (`auto` / `needs_owner`) with a
concrete action each:

- `recorded-waiver, nothing to do` — never re-litigate waivers.
- `agent-fixable now via vf_skill(<kind>)` — `auto: true`, apply it.
- `owner call (…) — see vf_skill(<kind>)` — diagnose, stage the artifact,
  file the exact question.
- `no skill registered — research, fix, vf_skill_propose` — the research
  loop (§4).

…plus one `recommended` line for the unit as a whole:

| recommended | meaning | next tool |
|---|---|---|
| `blocked-owner: needs …` | gate fails | stop, report what is missing |
| `ready-launch` | gate passes, path free | `vf_launch` |
| `ready-queue` | gate passes, path busy | `vf_queue` |
| `awaiting-ears` | final exists | hands off to owner ears/seal |

Real example (ch14 while shiva renders): gate green+approved,
`ready-queue`, 4 waived items recorded, 9 open white-gap/stuck-term items
routed to owner calls.

### Act

**`vf_launch(project, unit, ship=true)`** — renders one unit detached via
`batch.py --ship` (or volume-only with `ship=false`). Enforces gate, then
one-video law; returns `{launched, pid, log}` or `{launched: false,
reason}`. Logs to `/tmp/vf_mcp_<stem>.log`; batch detail also lands in
`/tmp/batch.log`. Never kills anything to make room.

**`vf_queue(project, unit, ship=true, max_wait_h=12)`** — same gate, but
when the path is busy it spawns a detached waiter (registered on the board
as `processes/queue-<stem>`) that polls every 30s and launches batch into
the next gap itself — the agent never sleep-blocks. Re-checks the gate at
launch time. If the path is free it launches immediately (same code path as
`vf_launch`).

**`vf_pack(project, units, publish=true)`** — zips shipped finals
(`ZIP_STORED`, no recompress — mp4s don't shrink) as
`<series>-<first>-<last>.zip` (contiguous) or `<series>-<a>+<b>.zip`,
checks volume room first, lists units with no final instead of failing,
optionally publishes. Built from the exact flow that shipped the
`tantrasara-ch15-22.zip` download.

**`vf_publish(local_path, key)`** — R2 upload with proof: allowlist (local
must live under `~/vol`, key like `tantrasara/<name>.ext`, no `..`),
`rclone copyto --local-no-check-updated` (volume-mount mtimes flutter and
plain copyto dies on phantom "source updated" errors), lsl size match, then
HEAD `Content-Length` match. Returns the public URL only on byte match;
anything else is `{published: false, reason}` with the evidence attached.

**`vf_skill_propose(kind, content, web_query="", auto=false)`** — stages a
researched skill: writes `core/skills/<kind>.md`, registers it
(`needs_owner` defaults to `not auto`). Kinds are `[a-z0-9-]{3,40}`.
Staging only — review the file, verify the fix it describes, then commit
skill + fix together (the flow law). `auto: true` is a safety claim: set it
only if agents may apply the skill unsupervised.

**`vf_motion(status="", lane="", query="")`** — the motion emblem bank:
GIF motifs with depictions, placements, maker briefs, and the wanted
queue. Filter by status (`banked`, `banked-described`, `wanted`), lane,
or free text. Read-only; ChatGPT works the `wanted` queue from here.

### Resources

- `vf://registry` — live `REGISTRY.json` (milestones, locks, processes,
  observations).
- `vf://render-gate` — the gate law in one object (for agents that need the
  rule, not the board).
- `vf://visuals` — house visual law + GIF maker sheet + draw prompt
  (`docs/VISUALS.md`, `docs/GIFS.md`, `core/art_bank/draw-prompt.md`).

## 4. Processes end to end

### Running the line (the daily loop)

`vf_status` → `vf_units` → pick a unit → `vf_triage` → follow `recommended`.
Fix `auto` issues via `vf_skill`; stage owner questions for the rest.
`vf_launch`/`vf_queue` → `vf_logs` → `vf_finals`. Close with `vf_check`
when code changed. Owner ears dispose; nobody else seals.

### Research → skill (web search to prescription)

The server never searches the web — scholarship happens with the agent's
own tools, staging happens here:

1. `vf_triage` reports "no skill registered" for a kind.
2. Read neighboring skills first (`white-gap` before inventing a pacing
   skill; `verse-term-unheld` before a cue skill) — most new issues are
   variants.
3. Research outside (web search, `docs/`, git history, the failing artifact).
   The skill's `web_query` field should be the query that would find the
   answer again.
4. `vf_skill_propose` with symptom → diagnosis → fix → process note. If the
   fix touches builders, implement + test it first.
5. Re-run the checker, re-triage, confirm the class clears, commit skill +
   fix together. A skill without a proven fix is a wish.

### Publishing a download

`vf_pack(project, "15,16,17,18,19,20,21,22")` → `{"packed": true,
"bytes": …, "upload": {"published": true, "url": …, "verified":
"HEAD-byte-match"}}` → hand the URL out. If `missing` is non-empty, those
units never shipped — triage them, don't re-zip blindly.

## 5. Skills reference

`vf_skills` is the live table (kind → file, `auto`, `needs_owner`); query
it rather than memorizing. At the time of writing, 15 skills:
canon-shape, cue-model, empty-gloss, hold-scan-red, list-geometry,
machine-deva, missing-audio, stack-crash, stale-verse-hold, stuck-term,
tts-ready, verse-deva-no-english, verse-gloss-missing, verse-term-unheld,
white-gap. Known-auto (agent applies now): missing-audio,
verse-term-unheld. Everything else routes through the owner except recorded
waivers, which are done and never re-litigated. Full routing logic is one
call away: `vf_triage`.

## 6. What is NOT here (on purpose)

No approve / waive / seal / ears tools. No glossary editing. No series-data
writes. No kill switches for other units' builds. If an agent needs any of
these, that is the system telling it to stop and ask the owner — the gap is
the guardrail.

## 7. Troubleshooting

- **Launch refused, "video path busy"** — normal. `vf_queue` and walk away.
  Never kill another build to jump the queue; the overnight supervisor's
  `drain()` will simply wait for you if you win a gap fairly.
- **Launch/queue refused on gate** — fix the storyboard to green, or get
  approval. There is no override flag and there never will be.
- **`/tmp` 100%** — batch tmp (`*_full.mp4`, `stage_*`, `verify_frames`,
  `probes`) leaks when a unit fails after shipping. Sweep stale transients
  only: never model caches (whisper, MMS onnx, `mmsmod`), never another
  lane's dirs, never live `mmsclip` / `mms_grp.f32` while a build runs.
  `vf_status` shows `tmp_free_gb` — check it before launching big units.
- **Mount flakes** (`Input/output error`, phantom mtime changes, `ls`
  ENOENT that self-heals): retry the read, or `rclone copy` the file down.
  `stage ..._blocks` disappearing mid-listing is the same flake.
- **R2 501 `NotImplemented` on first attempt** — transient; the second
  attempt succeeds (batch ship loop does 3 attempts; so does experience).
- **Root `mcp_server.py`** — must never exist here; sleepdraw owns that
  module name and `propose_draws` imports it bare. Ours is
  `vf_mcp_server.py` (`TestMcpServerNameLock`).
- **ch6 vs ch06** — legacy stem split; the server probes both digit
  variants for finals/approvals/issues/parts. New lanes: one stem scheme
  (docs/UNITS.md).
- **pytest green, check.py red (or vice versa)** — the runners resolve
  `sys.path` differently (`python -m` prepends cwd). Tests must pass under
  both; load modules by path (importlib), never by bare name.
- **opencode doesn't see the server** — restart opencode (no hot reload).
  Broken config: `OPENCODE_DISABLE_PROJECT_CONFIG=1` or `OPENCODE_PURE=1`
  to start, fix, restart. Keep `$schema` in the config file.
- **A tool hangs past timeout** — `vf_tests full` and `vf_check` need the
  180s server timeout; with the default 30s opencode kills them mid-run and
  it looks like a server bug. It isn't.

## 8. FAQ

- *Why did triage say ready-queue and not launch?* Builders were running.
  Queue; the waiter launches into the next gap and the supervisor's drain
  absorbs the delay.
- *The unit has open issues — can it still render?* Yes, if the gate
  passes. Issues are a work list, not a gate (owner order). `vf_launch`
  will say so by launching.
- *Who seals a video?* The owner, ears first. `awaiting-ears` is a full
  stop for agents.
- *Where do I watch a render?* The `log` path returned by launch/queue,
  via `vf_logs`, plus `/tmp/batch.log` for builder detail.
- *How do I add a tool?* Implement in `vf_mcp_server.py` (pure helpers up
  top, tested in `tests/test_mcp.py`), smoke it over stdio, extend this
  doc's §3, run `check.py` to CANONICAL, commit + push. Reads before
  writes; gates before launches; no owner-only acts, ever.
