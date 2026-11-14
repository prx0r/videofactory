# PRODUCTS — every finished output on R2 (`r2:svread-audio/`)

Single note of all outputs + finished products and where they live.
Updated 2026-11-14. New session products first, then pre-existing libraries.

## A. This session (audio-only)

| Product | R2 key(s) | Status |
|---|---|---|
| nibbana ch.1–10 audio (granny/man TTS) | `nibbana/n01_audio.mp3` … `n10_audio.mp3` | n01–n07 ✅ live; n08–n10 rendering (n01/n04 rework queued) |
| paramarthasara p01–p07 audio | `paramarthasara/pNN_audio.mp3` | queued behind nibbana |
| tibetan-dead d01–d05 audio | `tibetan-dead/dNN_audio.mp3` | queued |
| deathworks w01–w05 audio | `deathworks/<stem>_audio.mp3` | queued |
| paratrishika v01–v36 audio | `paratrishika/vNN_audio.mp3` | 36/36 approved; queued last (incl. waiter for fixed 14) |
| analayo Rung A CORE draft (2h05m) + gaps | `analayo/rungA_core_draft.mp3`, `analayo/rungA_gaps.json` | ✅ live (DRAFT: 20 spans silent, 7 lecs missing) |
| shiva-unfunny STANDARD walks 0/A/B | `shiva/standard_walk_{0,A,B}.mp3` | ✅ live (byte-exact assemblies; owner ears still required) |

Render recipe (all lanes): per-unit `render_chapter` → `assemble_chapter` →
`rclone copyto` + size verify → delete local cache. See `AUDIO-REGISTRY.md`.

## B. Pre-existing finished libraries (untouched)

- **Stotra chant library** — `audio/` (48 dirs): per-verse/per-hymn mp3s incl.
  `shivastotravali_1..20`, `spandakarika`, `bhairavastava`, etc.
- **Śivastotrāvalī chant fulls** — `shivastotravali/shivastotravali-fulls-20261102.zip`
  (126 MB). NOTE: this is the **chant** (Utpaladeva verses), distinct from the
  **slang audiobook** below.
- **Read audiobooks** — `read/` (`bhairavastava/`, `paramarthasara/` parts),
  `read-v2/` (`bhairavastava/`).
- **Funny lanes (shipped video)** — `tantrasara/` (`chNN_full*.mp4` + audio),
  `shiva/` (`sNN_full.mp4` + verify JSONs; plus nibbana demo mp4s).
- **Voice references** — `voices/` (seat comparisons), `shorts/` (granny/roady
  wavs + mp4s), `parables/song04-granny-full.mp3`, `ytpack/ytpack-studio.zip`.
- **Alignment data** — `align/*.json` (not audio, kept for reference).

## C. Chant vs slang-audiobook (do not confuse)

- **Chant** = Sanskrit verses voiced (fish_audio 450/450 + R2 `audio/` +
  fulls zip). COMPLETE. No further work.
- **Slang audiobook** = English irreverent reading with Sanskrit + commentary
  (ChatGPT exports `ayoutube/ChatGPT-Continue Śivastotrāvalī Part XXVII…` and
  `…Review Śivastotrāvalī Progress…`, extending to Part XLVI / Hymn XX).
  Staged at `/tmp/sivastotravali/`. NOT built — needs text extraction + TTS.

## D. Deliberately not rendered

- analayo lecture sources stay in git (sparse clone); only cutplans + Rung A
  draft live. No further analayo audio without owner override of the
  no-render law.
- Vatulanatha: text-complete; audio blocked on 9 owner decisions (#1–2 done).

### Preview clips (for listening; regenerate share links via \`rclone link\` — presigned URLs expire)
- `nibbana/previews/n02_intro.mp3` (title + cold open, 75s)
- `nibbana/previews/n02_teaching.mp3` (mid-chapter teaching, 75s)
- `analayo/previews/opening.mp3` (motto + first question, 90s)
- Full takes: `nibbana/n02_audio.mp3`, `analayo/rungA_core_final.mp3`, `shiva/std/1_1_B.mp3`

## E. Shorts dependency (next phase)

Shorts slice the content-hash **group-wav cache**, but the audio pass deletes
wavs after publishing the mp3. Resolution for the shorts phase: the shorts
cutter selects source bids -> if a group wav is missing, render just those
groups (one Fish call each, cheap) before slicing — never re-render the whole
unit. Alternative: retain per-lane group wavs on R2 and pull on demand.
See `docs/SHORTS-PROCESS.md`.
