# ART-PIPELINE — how sealed art gets into video (agent runbook)

The convergence, in one line: **translation-work argues → P1 seals compress →
art-bank indexes → sleepdraw renders → videofactory draws → series ships.**
Nothing floats: every image cites the brief that cites the verses that cite
the source bytes (see translation-work TECHNICAL-SPEC §2 for the byte story).

## 1. Clone map (one root, siblings side by side)

```bash
mkdir -p /root && cd /root
for r in translation-work svread sanskritbench sleepdraw videofactory tantrasara ipvv openpatala; do
  git clone https://github.com/prx0r/$r.git $r
done
```

| Repo | Provides the pipeline | You need it if |
|------|----------------------|----------------|
| `translation-work` | Translation layers + all P1 seal briefs (`<work>/*SEAL*.md`, `P1-INDEX.md`) | reading or extending any seal; verse anchors |
| `sleepdraw` | Renderer: `mcp_server.py` (presets/seal_prompt/render_seal), lora presets, techdou etch | generating or reviewing any art |
| `videofactory` | Assembly: `core/builders/propose_draws.py`, `holds.draws_for`, `core/art_bank/REGISTRY.json` | proposing draws, building video |
| `tantrasara` | Series data: storyboards, drops, review timelines, glossary | working tantrasara gaps |
| `svread` | Scholar workspace (claims, PUSHBACK, audit) — adjacent, not required | claim-linked essays |
| `sanskritbench` / `ipvv` / `openpatala` | Verification + sources — adjacent, not required | source disputes |

Pinned 2026-11-05 (re-verify with `git rev-parse HEAD`): translation-work
`d0762b9`, svread `cb68175`, sanskritbench `7bd466d`, sleepdraw `8095c83`,
videofactory `67881b9`, tantrasara `d32acd4`, ipvv `365c1221`,
openpatala `4147a19`.

Do NOT clone all of sleepdraw's R2 zips (gigabytes) — the MCP needs only
`lora2-inv.yaml` + `mcp_server.py`. Do NOT copy P1 seal files — the bank
holds pointers; canonical briefs live in translation-work.

## 2. The seal economy (why it converges instead of drifting)

- A **seal brief** (`*SEAL*.md`) justifies an image element-by-element
  against verses + C1 essence + rasa (see the spider exemplar:
  `core/art_bank/seals/spider-song04-seal.md`, vendored from
  `translation-work/paramarthasara/P1-SONG04-SEAL.md`). No element without
  two anchors = no drift, no invented symbolism.
- A **bank entry** (`core/art_bank/REGISTRY.json`, `trika-art-bank/1`)
  indexes the brief + base + seed + prompt + asset + recipe. Statuses:
  `OWNER-APPROVED-ANGLE` (exemplar), `MACHINE_DRAFT` (P1 pointers),
  `PROPOSED` (queued subjects like mala — render only after anchors).
- A **render** is hermetic when prompt + preset SHA + env + seed are
  recorded (recipe.json). sleepdraw's `render_seal` refuses without
  explicit `confirm_paid:true` — paid Bailian generation never happens
  by accident.
- A **draw** is owner-called: `draws_chNN.json` `{start_bid: {asset,
  complete_bid, clear, fade, why}}` beside the drops file. `why` fails
  loud when missing. Proposed files (`draws_chNN.proposed.json`) can
  NEVER render — `draws_for` matches the exact name only.

## 3. Loop (the actual workflow)

```
timeline WHITE gap (+ white-map priority) → propose_draws (bank-first)
  →  projects/<lane>/proposed/draws_chNN.proposed.json (in-factory staging;
      draws_for matches draws_chNN.json exactly, so staged files NEVER render)
  →  owner/agent review: accept bank asset | render new seal (confirm_paid)
  →  promote: copy to series drops dir as draws_chNN.json {asset,
      complete_bid, clear, fade, why} → build fades it in from white
```

Commands:

```bash
# 1. draft seals for chapter gaps (free, no generation)
python3 core/builders/propose_draws.py /root/tantrasara/storyboard_ch20.json \
  /root/tantrasara/review/ch20/timeline.md
# 2. seal prompt for one gap (free, deterministic)
python3 /root/sleepdraw/mcp_server.py seal_prompt '{"text": "...", "chapter": "tantrasara-20"}'
# 3. render ONE seal (SPENDS ~CNY 0.18 — owner confirms first)
python3 /root/sleepdraw/mcp_server.py render_seal \
  '{"prompt": "...", "name": "ch20-b88-mala", "confirm_paid": true}'
# same over MCP stdio: {"jsonrpc":"2.0","id":1,"method":"tools/call",
#   "params":{"name":"render_seal","arguments":{...}}}
```

## 4. Rules that keep it honest

1. Bank-first: never draft fresh when the bank holds the subject.
2. New seal = new base (spent-log in P1-INDEX; a base renders once).
3. No render without verse + essence anchors (PROPOSED stays queued).
4. No asset without a recipe; no draw without a why.
5. White-ground chapters use lora2-inv (black ink on white). lora2
   white-on-black is sleep channels only — never mix.
6. Proposed files are not promotion. Promotion is a human/owner write
   of `draws_chNN.json`, never an agent default.
