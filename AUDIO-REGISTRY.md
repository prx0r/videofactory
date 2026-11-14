# AUDIO REGISTRY — working board (2026-11-14)

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
| **Shiva-sutras (UNFUNNY / STANDARD)** | `~/shiva-sutras` | ⛔ NOT BUILT | 77-verse build; only v1.1 proof exists. Needs `tools/build_all.py`. |
| Śivastotrāvalī (chant) | `~/kashmir_audio`, `~/fish_audio`, `~/stotras` | ✅ DONE | 450/450 verses, 450 wav + 450 mp3, 20 hymns; fulls zip on R2 |
| Śivastotrāvalī (slang audiobook) | R2 `ayoutube` exports | ⏳ SOURCE ONLY | new ChatGPT Parts XXVII/XLV on R2 `ayoutube/`; extends to Part XLVI / Hymn XX |
| analayo-nibbana | `~/analayo-nibbana` (GitHub `prx0r/analayo-nibbana`) | ✅ DONE | 33/33 cutplans; audio deliberately NOT rendered (repo law) |
| vatulanatha ("vanustaya") | `~/vatulanatha` | ⛔ BLOCKED | text-complete; 9 owner decisions + TTS not run |
| nibbana | `~/nibbana` | ⏳ RENDERING | 10 units approved; n02 live on R2 |
| paramarthasara | `~/paramarthasara` | ⏳ QUEUED | 7 units approved |
| tibetan-dead | `~/tibetan-dead` | ⏳ QUEUED | 5 units approved |
| deathworks | `~/deathworks` | ⏳ QUEUED | 5 units approved |
| paratrishika | `~/paratrishika` | ⏳ QUEUED | 22 approved; 14 blocked (owner disposition) |

## Audio pipeline (disk-light, no visuals)

Per unit: `render_chapter` → `assemble_chapter` → `rclone copyto` r2 +
byte-verify → delete work dir **only on success**. Isolated work dir per unit
under `<lane>/renders/_work/<stem>`.

- Script: `/tmp/audio_to_r2.sh` (reproducible; see "Commands").
- Env: `VF_TTS=~/videofactory/core/builders/tts_line.py` (pronunciation-fixed
  copy; frozen shiva tool untouched), `VF_PROJECT/VF_REPO/VF_RENDERS` per lane.
- R2 key shape: `r2:svread-audio/<lane>/<stem>_audio.mp3`.
- Combined mp3s are the finished audio deliverable; wav group cache is
  disposable.

### Progress (updated as it runs)

- nibbana n02 ✅ `r2:svread-audio/nibbana/n02_audio.mp3` (49.6 min, byte-match)
- nibbana n01..n10 ⏳ (n01 has one ~5-min intro TTS group; timeout raised to 1200s)
- paramarthasara / tibetan-dead / deathworks / paratrishika — queued behind

## Fixes shipped this session

- **TTS pronunciation map** (`core/builders/tts_line.py`, factory copy):
  `phowa/Phowa/PHOWA → powah` (reads "power", not "fower"/spelled out);
  `Parātrīśikāvivaraṇa → Paratrishika Vivarana`; strip HTML entities
  (`&#124;`, `&amp;`) before voicing.
- **Data recast** — pure-symbol voiced blocks (e.g. `'; ]'`, metre marks) and
  the Greek-script duplicate (deathworks b537) recast to `voice:none` so they
  never produce empty/garbled wavs. Affected: paratrishika 37 blocks / deathworks 3.
- **render_chapter TTS timeout** 300s → 1200s (n01's ~5-min intro block
  false-failed under the old cap).
- **MCP `vf_publish` allowlist** widened from `tantrasara|shiva|factory` to any
  lane prefix (new lanes literally could not publish before).

## Audio cleaning status

- `vf_speakcheck` = 0 hazards on all 5 lanes (no hashheads/emphasis/tables).
- Entities, `>` blockquote markers, pure punctuation, Greek handled as above.
- Glossaries all-proposed (no confirmed terms) — fine for audio (voice-only);
  relevant only at the future visual/card stage.

## Blockers / owner decisions

1. **Shiva-sutras UNFUNNY (STANDARD 77)** — run full `build_all`? Multi-hour,
   gated (pilot → batch → QA → assemble walks 0/A/B/C). Not a concat.
2. **vatulanatha** — 9 decisions in its `HANDOFF.md` decision queue, then TTS.
3. **paratrishika 14 units** (v01,04,05,06,08,09,12,14,15,19,26,27,28,31) —
   `section has no granny block` warnings; `PARA-INTAKE.md` says structural,
   "never relaxed by agents". Need owner: waive, or add narration bridges.

## Commands (resume)

```bash
# audio-only, disk-light, all queued lanes:
nohup /tmp/audio_to_r2.sh >/dev/null 2>&1 &

# single unit, disk-light:
export VF_TTS=$HOME/videofactory/core/builders/tts_line.py
VF_PROJECT=nibbana VF_REPO=$HOME/nibbana VF_RENDERS=$HOME/vol/nibbana/renders/_work/nXX \
  python3 ~/videofactory/core/builders/render_chapter.py \
  ~/nibbana/storyboards/storyboard_nXX.json
# then assemble + publish:
VF_PROJECT=nibbana VF_REPO=$HOME/nibbana VF_RENDERS=<work> \
  python3 ~/videofactory/core/builders/assemble_chapter.py \
  ~/nibbana/storyboards/storyboard_nXX.json <work>/nXX.mp3
rclone copyto <work>/nXX.mp3 r2:svread-audio/nibbana/nXX_audio.mp3 --transfers 1
```

## Gotchas learned

- Total disk is tight (96G). `~/.cache` and the full analayo clone were the
  hogs; analayo is now a blobless/sparse clone (4.4G → 12M, text/cutplans only).
- n01's entire cold-open is one TTS group (~5 min) — expect a slow first group.
- Do NOT delete a unit's cache unless its mp3 published (byte-verified).
