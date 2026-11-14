# Extraction repos — status & render readiness (2026-11-14)

Notice PR: two new public extraction repos exist and are render-ready against
this stack's fish/direction law. Nothing in this repo changes operationally;
this doc is the cross-repo pointer.

## Repos

| repo | contents | size | rights |
|---|---|---|---|
| **prx0r/vivek** | Complete Works of Swami Vivekananda — vols 1–9 + introduction, unpublished, appendices (source: ramakrishnavivekananda.info) | 1,208,442 words · 896-chapter catalogue (genre, dates, places) · one `.md` per volume | PD (author d. 1902) |
| **prx0r/ramakrishna** | The Gospel of Râmakrishna, tr. Abhedananda 1907 — introduction + 14 chapters | 82,292 words · per-chapter `.md` + catalogue · curation complete: **Complete Sessions** emitted (313 KEEP / 76 CUT, 77,468 words) + unused/COVERAGE/ledger | PD (1907 ed.) |

Both repos ship `tools/`, `output/`, catalogues and READMEs; HTML caches are
gitignored.

## Render pipeline (this repo's law, ported)

- `tools/batch_voices.py` (in prx0r/vivek) — fish scripting copied from this
  stack: **FISH-DIRECTION** S2 markers only (`[break]` / `[long-break]`,
  tag-prefix-only with `stripped == original` audit), model
  `fish-audio/s2.1-pro-free` pinned, `sha1(voice|directed)` group cache,
  receipts/stats, dry-run.
- **Casting** (owner rule): voice `394578d869ee4f99aa6fa500ba664528` (old man)
  = the Master (Vivekananda / Ramakrishna); voice
  `614f8afd83f841048c040b2c6234d2c1` (granny) = host — titles, attributions,
  questioner, narration.
- **House norm**: −21 dB mean / −1.5 dB peak, gain clamped ±12.
- **Rule 8**: hub runs zero ffmpeg — fish → concat → norm → encode all on
  vps, push straight to `r2:longform-audio/vivek/` (vps→R2 ≈13 MB/s;
  hub pull ≈13 KB/s).

## Live queue (as of this PR)

- **25 slugs**, strictly serial: 13 Complete Talks first (each an individual
  R2 file: `talks/<slug>.mp3`), then the 12 volumes with talk block-ranges
  excluded so every word renders exactly once.
- ~5,900 groups ≈ 33 h ETA; monitoring: `tools/tts_status.py` (console) +
  `--serve 8612` dashboard + per-slug `notify-send` + log.
- **Talks complete: 13/13 in R2** (6 h 37 min total; `TALKS-INDEX.md`).
- Volume batch running: vols 1–9 + unpublished + appendices, ~3.4k groups,
  ETA ~35–40 h, self-healing (watchdog + flock + retries + done markers).
- **Language guard:** fish cannot read Devanagari/Bengali — Indic blocks are
  never voiced (4,452 blocks / 219,792 words skipped, documented in
  `LANGUAGE-POLICY.md`; voice-QA samples in `r2:.../samples/`).

## Shorts (ready, deliberately NOT in the queue)

- **102 extract-only shorts**, 60–120 s, standalone-checked, 15 themes across
  the full corpus: `shorts/ledger.jsonl`, `shorts/REVIEW.md` (full text),
  `shorts/TOPICS.md` in prx0r/vivek.
- **Tiered after full manual review:** S26 / A50 / B21 / C5 (`shorts/TIERS.md`),
  duplicate pass done, 5 re-spans applied, zero Indic spans.
- Nothing renders until the owner approves; `tools/render_shorts.py --tier S
  --render` voices an approved tier (old-man voice, same norm, `shorts/<id>.mp3`).
- `tools/shorts_reuse.py`: 28 shorts are exact fish-free slices of already
  rendered group audio.

## Process notes

Both repos carry append-only `PROCESS-NOTES.md` (pipeline law, runbook,
mistakes log) — read those before changing anything.

## Triggering a render from this stack

```bash
cd ~/Documents/patala/vivekananda-complete-works
python3 tools/batch_voices.py --slug talks/<slug> --dry-run   # plan
python3 tools/batch_voices.py --slug talks/<slug>             # render → R2
python3 tools/tts_status.py                                   # progress
```
