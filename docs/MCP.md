# MCP control plane (videofactory MCP server, stdio)

`vf_mcp_server.py` exposes the whole factory to agents over MCP stdio
(registered in opencode as `videofactory`; restart opencode after config
changes). 18 tools + 2 resources. Reads never write; the five act tools
enforce factory law instead of trusting the caller.

## The law the server enforces

- Render gate (owner order 2026-11-06): storyboard green + owner approval is
  the ONLY gate. `vf_launch` / `vf_queue` refuse anything else.
- One video build at a time: launch refuses while builders run; queue waits.
- Free Fish only, UNCAST never defaults, Deva/gloss owner-only — these live
  in the builders, the server never bypasses them.
- Deliberately NOT exposed: approvals, waivers, ears, seals. Owner acts stay
  human. Agents get everything up to the gate and the launch past it.

## Processes (which tools, in order)

### Run the line: status → triage → skill → gate → launch
1. `vf_projects` — discover lanes (tantrasara 22 chNN, shiva-sutras 78 sNN).
2. `vf_status` — board: gate mode, milestones, live builders, vol/tmp free,
   driver log tails. Call first, always.
3. `vf_units(project)` — stage table. `vf_unit(project, unit)` — deep state
   (approval, final bytes, ship verdict, parts).
4. `vf_triage(project, unit)` — THE decision tool: gate verdict, per-issue
   routing (agent-fixable / owner call / recorded-waiver), recommended step
   (`ready-launch` → `vf_launch`, `ready-queue` → `vf_queue`,
   `blocked-owner` → stop and report, `awaiting-ears` → hands off).
5. `vf_issues` + `vf_skill(kind)` — issue detail + full fix prescription.
6. `vf_launch` (path free) or `vf_queue` (path busy — waiter polls and
   launches into the next gap, never sleep-blocks the agent).
7. `vf_logs` — follow the unit log. `vf_finals` — confirm the mp4 + URL.

### Research → skill loop (web search to prescription)
1. Agent hits an issue kind with no skill (`vf_triage` says "no skill
   registered").
2. Agent researches with its OWN tools (web search, repo archaeology). The
   server never searches the web — scholarship happens outside, staging
   inside.
3. `vf_skill(kind)` for neighboring kinds first — most "new" issues are
   variants (white-gap vs stuck-term).
4. `vf_skill_propose(kind, content, web_query, auto)` — stages
   `core/skills/<kind>.md` + REGISTRY entry (`auto: true` ONLY if agents may
   apply it unsupervised; otherwise `needs_owner: true`). Commit skill + fix
   together, same commit as the fix (flow law in skills/REGISTRY.json).
5. Re-run the checker, re-triage, confirm the issue class clears.

### Publish a download (pack → ship → verify)
`vf_pack(project, units, publish=true)` zips shipped finals (stored, no
recompress) and uploads via the same path as `vf_publish`: rclone copyto
with `--local-no-check-updated` (volume-mount mtimes flutter — plain copyto
fails phantom "source updated" errors), then lsl size match, then HEAD
Content-Length match. Returns the public URL only on byte match.

## When to use what (and what NOT to touch)

| Situation | Tool | Never do this instead |
|---|---|---|
| What should I do about unit X? | `vf_triage` | guess from raw files |
| Is the path free / what runs? | `vf_status` | `ps` + vibes |
| Render now | `vf_launch` (refuses if busy/ungated) | run batch.py by hand |
| Render when free | `vf_queue` | sleep-loop polling |
| Fix an issue | `vf_skill(kind)` then apply | improvise the fix |
| New issue class solved | `vf_skill_propose` + commit | keep it in chat |
| Ship a zip / file | `vf_pack` / `vf_publish` | bare rclone (no verify) |
| Factory healthy? | `vf_check` (CANONICAL?) | assume |
| Suite green? | `vf_tests` (quick default) | skip tests |

Agents must not: approve, waive, seal (no tools — by design); edit frozen
series data; run two video builds; `rclone copy` to a filename (creates a
directory — always copyto); trust mount reads blindly (retry).

## Skills (linked, not pasted)

`vf_skills` lists every kind with `auto` / `needs_owner`. `vf_skill(kind)`
serves the full markdown. Severity routing:

- `auto: true` (missing-audio, verse-term-unheld): agent applies the skill
  now, re-checks, moves on.
- `needs_owner: true` (white-gap, stuck-term, machine-deva, verse cards…):
  agent diagnoses, stages the artifact (draw spec, mined gloss), and files
  the exact owner question. Owner confirms in bulk; engineer flips status,
  never edits glosses silently.
- waived-owner: recorded, nothing to do — never re-litigate.

## Troubleshooting

- `vf_launch` refuses "video path busy": normal — use `vf_queue`, or wait.
  Never kill another unit's build to jump the queue.
- `vf_launch`/`vf_queue` refuse on gate: fix the storyboard (green) or get
  approval (owner). No flag overrides this.
- `/tmp` 100%: batch tmp (`*_full.mp4`, `stage_*`, `verify_frames`,
  `probes`) leaks when a unit fails post-ship; sweep stale transients only —
  never model caches (whisper/MMS), never another lane's dirs, never live
  `mmsclip`/`mms_grp.f32` while a build runs.
- Mount flakes (`Input/output error`, phantom mtime changes): retry, or
  `rclone copy` down. `vf_publish` already passes
  `--local-no-check-updated` for this.
- `NotImplemented: Not Implemented` (501) on first R2 attempt: transient —
  retry succeeds (the batch ship loop does 3 attempts).
- `import mcp_server` collisions: root must NEVER contain `mcp_server.py`
  (sleepdraw owns that module name; ours is `vf_mcp_server.py` — lock test
  in tests/test_postmortem.py).
- ch6 vs ch06: legacy stem split — the server tries both digit variants for
  finals/approvals/issues. New lanes: keep one stem scheme (docs/UNITS.md).
- Suite runner differences: pytest and `unittest discover` resolve sys.path
  differently (`python -m` puts cwd first). Tests must pass under BOTH —
  check.py runs unittest; never rely on bare module names (importlib by path).
- Config edits: validate JSON, keep `$schema`, restart opencode (no hot
  reload). If opencode won't start, `OPENCODE_DISABLE_PROJECT_CONFIG=1` /
  `OPENCODE_PURE=1` escape hatches (customize-opencode skill).
