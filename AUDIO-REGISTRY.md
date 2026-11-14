# AUDIO REGISTRY — working board (updated 2026-11-14 ~06:45 UTC)

Single source of truth for the "all audio, audio-only" session. No visuals in
this phase. Update this file as work lands; it is the shared board other
agents read.

## Goal

Generate **all audio** for every READY track and publish to R2, disk-light
(render → assemble mp3 → upload → delete local cache). Visuals are out of
scope for this session.

## Track status

| Track | Repo | State | Notes |
|---|---|---|---|
| Tantrasara (funny) | `~/tantrasara` | ✅ DONE | 22 shipped (owner-closed 2026-11-11) |
| Shiva-sutras (funny) | `~/tantrasara/shiva` | ✅ DONE | 77/78 shipped, s29 waived (owner-closed) |
| **Shiva-sutras (UNFUNNY / STANDARD)** | `~/shiva-sutras` | ✅ BUILT | 77 proofs/layer (0/A/B) + walks 0/A/B on R2; owner ears still required before any master ships. |
| Śivastotrāvalī (chant) | `~/kashmir_audio`, `~/fish_audio`, `~/stotras` | ✅ DONE | 450/450 verses, 450 wav + 450 mp3, 20 hymns; fulls zip on R2 |
| Śivastotrāvalī (slang audiobook) | `~/shiva-sutras` + R2 `ayoutube` | ⏳ SOURCE | new ChatGPT Parts XXVII/XLV on R2; extends to Part XLVI / Hymn XX |
| analayo-nibbana | `~/analayo-nibbana` (sparse, text-only) | ✅ FINAL ON R2 | Rung A `rungA_core_final.mp3` (2h04m, 0 gaps, byte-verified) + black-screen mp4 (below); draft kept; sources cleared (recoverable). |
| vatulanatha ("vanustaya") | `~/vatulanatha` | ⏸ ON HOLD (owner) | #1-3 applied (order, home, C-rule); G0-G10 PASS. Left for later. Still needs: #4-9, source audio (missing everywhere), TTS. |
| nibbana | `~/nibbana` | ⏳ RENDERING (master queue) | n01-n05 on R2; n06-n10 rendering serially, per-unit publish+delete. |
| paramarthasara | `~/paramarthasara` | ⏳ QUEUED | 7 approved |
| tibetan-dead | `~/tibetan-dead` | ⏳ QUEUED | 5 approved |
| deathworks | `~/deathworks` | ⏳ QUEUED | 5 approved |
| paratrishika | `~/paratrishika` | ⏳ READY 36/36 | 14 fixed (section merges + 2 type fixes), all approved; queued |

## Audio pipeline (disk-light, no visuals)

Per unit: `render_chapter` → `assemble_chapter` → `rclone copyto` r2 +
byte-verify → delete work dir **only on success**. Isolated per-unit work dir
under `<lane>/renders/_work/<stem>`.

- Script: `/tmp/audio_to_r2.sh` (nibbana→para→tibetan→deathworks→paratrishika).
  Analayo has its own builder (`/tmp/analayo_build.py`); shiva-unfunny runs
  its repo-native `tools/build_all.py`.
- Env: `VF_TTS=~/videofactory/core/builders/tts_line.py` (pronunciation-fixed
  copy; frozen shiva tool untouched), `VF_PROJECT/VF_REPO/VF_RENDERS` per lane.
- R2 key shape: `r2:svread-audio/<lane>/<stem>_audio.mp3`.
- Combined mp3s are the finished audio deliverable; wav group cache is
  disposable.

### Progress

- nibbana n02 ✅ `nibbana/n02_audio.mp3` (49.6 min) · n01 ✅ · n03+ rendering
- paramarthasara / tibetan-dead / deathworks / paratrishika-36 queued behind

## Fixes shipped this session

- **TTS pronunciation map** (`core/builders/tts_line.py`, factory copy):
  `phowa/Phowa/PHOWA → powah` (reads "power", not "fower"/spelled out);
  `Parātrīśikāvivaraṇa → Paratrishika Vivarana`; strip HTML entities
  (`&#124;`, `&amp;`) before voicing.
- **Data recast** — pure-symbol voiced blocks (e.g. `'; ]'`, metre marks) and
  the Greek-script duplicate (deathworks b537) recast to `voice:none` so they
  never produce empty/garbled wavs. Paratrishika: 14 structural sections merged
  into neighbouring granny sections + 2 validator-prescribed narration→dialogue
  type fixes; stored validation rebuilt; all 36 now gate-green.
- **Paratrishika spoken titles + dodgy-scan** — PART numerals and "Part XXX"
  stripped from `directed` only (record keeps PART numbers; do NOT rebuild
  validation without re-applying, as `validate()` recomputes `directed`);
  spoken Romans (Part/KSTS/verse/list) → English words; 35 ALL-CAPS citation
  labels → sentence case; 3 Continue-reading prompts silenced; broken
  apparatus/URL/symbol junk removed (real notes kept); 2 scansion blocks
  silenced; `√`→"root" in TTS map. Verse (64–774/unit) and man (1–43/unit)
  confirmed live. All 36 green + approved.
- **render_chapter TTS timeout** 300s → 1200s (n01 ~5-min intro block
  false-failed under the old cap).
- **Shiva-unfunny 1.1 dead-air FOUND+FIXED (2026-11-14)**: pilot verse's 6
  primary-source lecture cut-parts were stale-silent (-71dB) because
  `build_standard_verse.cut()` skips if the part exists (`if exists: return`) —
  a bad first build never regenerated. Deleted 1.1 intermediates, rebuilt verse,
  re-assembled walks 0/A/B, re-uploaded all byte-verified. All 77 verses now
  scanned: 0 silent cut-parts. (Lesson: delete intermediates before rebuilding
  a verse; guard hides stale audio.)
- **Shiva `build_all` pilot gate** — added missing `word_timestamps=True`
  (gate always counted 0 words without it; proofs were fine at ~494 words).
- **MCP `vf_publish` allowlist** widened from `tantrasara|shiva|factory` to any
  lane prefix (new lanes literally could not publish before).

## Audio cleaning status

- `vf_speakcheck` = 0 hazards on all 5 lanes (no hashheads/emphasis/tables).
- Entities, `>` blockquote markers, punctuation-only, Greek handled as above.
- Glossaries all-proposed (no confirmed terms) — fine for audio (voice-only);
  relevant only at the future card stage.

## Blockers / owner decisions (approved — executing)

1. **Shiva-sutras UNFUNNY (STANDARD 77)** — approved; `build_all` running:
   pilot → batch 76 → `qa_std` → assemble walks 0→A→B. No coda/Sharma (struck).
2. **vatulanatha** — 9 decisions approved; applying (#1 order fixes first),
   then TTS pipeline.
3. **paratrishika 14** — DONE (merged + approved + queued).

## Lane audiobook blockers (spec, 2026-11-14)

Solved before queueing — no gate blockers remain for audio:
- **H1 intro-thumbnail REDs are visual-only** (p01,p02,p03,p04,p06,p07,heist).
  Audio renders via `validate_storyboard_gate` (green+approval), which ignores
  H1/H8 planning estimates. `vf_gate` conflates them — do not treat H1 as an
  audio block. Deferred to the video stage.
- **Oversized TTS groups — split**: tibetan d01 (12k chars) and d02 (10k) exceeded
  the proven 7.3k single-call range. Split via filed drops at sentence breaks
  (d01: 6 splits, d02: 5 splits; 1s breaths). Now max 1.9k/5.7k. Approvals intact
  (drops are not SHA-pinned).
- **Tibetan b1 toll-bed drops FILED** (were `.proposed` only; `toll` key stripped
  as non-schema — pause+why preserved, 2.0s bed).
- **Monitor (within timeout, split only on actual FAIL)**: d04/d05 (~8k),
  n08 (7.0k)/n09 (7.4k), deathworks madman (8.7k)/heist (7.2k)/escape (6.3k),
  para max (5.8k). All <1200s TTS timeout; pipeline logs + continues on failure.
- Paratrishika 36/36 + nibbana n01-n04 already verified; master queue renders
  serially with per-unit publish+delete (disk law).

## Gotchas learned

- Total disk is tight (96G). `~/.cache` and the full analayo clone were the
  hogs; analayo is now a blobless/sparse clone (4.4G → 12M, text/cutplans only).
- The `vf_publish` MCP tool cannot publish new lanes until the server restarts
  with the allowlist fix; meanwhile publishing uses the identical rclone
  copyto+verify the tool performs.
- n01's entire cold-open is one TTS group (~5 min) — expect a slow first group.
- Do NOT delete a unit's cache unless its mp3 published (byte-verified).
- Launching heavy builds via shell `&` hangs this environment; use a Python
  `Popen(start_new_session=True)` detach instead.

## Commands (resume)

```bash
# audio-only, disk-light, all lanes (already running detached):
#   /tmp/audio_to_r2.sh  (nibbana -> paramarthasara -> tibetan-dead -> deathworks -> paratrishika)
# analayo Rung A (already running detached):
#   python3 /tmp/analayo_build.py
# shiva-unfunny STANDARD (already running detached):
#   python3 tools/build_all.py  (in ~/shiva-sutras)
# single unit, disk-light:
export VF_TTS=$HOME/videofactory/core/builders/tts_line.py
VF_PROJECT=nibbana VF_REPO=$HOME/nibbana VF_RENDERS=$HOME/vol/nibbana/renders/_work/nXX \
  python3 ~/videofactory/core/builders/render_chapter.py \
  ~/nibbana/storyboards/storyboard_nXX.json
```
