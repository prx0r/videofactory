# PROCESS-NOTES2 — session record: storyboard-first loop, chunk method, ch02 (2026-11-04)

For the next agent. Read START-HERE.md first, then this. Nothing here
renders without the owner's word; the tree is frozen mid-audit.

## What this session did (in order)

1. Killed all background renders. No video builds run until the owner
   blesses the storyboard state. `pkill` hangs on this box (D-state
   mount processes) — kill by PID from `/proc`, never by pattern.
2. Wrote the mistakes down first: M24 shipped stale ch02 without
   proofs or meta; M25 removed the one-video law and forked shadow
   builders; M26 half-flipped ch02 b2 (overrides popped, storyboard
   stale); M27 minted new R2 root keys instead of retiring stale ones.
3. Built the storyboard gate (`gate_storyboard.py`, repo): green check,
   drops exist + group-final + justified, intro thumbnail ≤60s, H8 no
   visual static past 60s (estimates @150wpm), glossary keys folded,
   confirmed terms carry citation Deva, literals square brackets.
   RED fails the render before it runs. Estimates flag; the measured
   video gate decides finally.
4. Fixed the laws the owner called wrong (same commit as code):
   GATES H1 + VISUAL + STANDARD — thumbnail holds the intro (first
   tone break), not the first chant. Optical header alignment ported
   from shiva (measured 137 vs 138 on ch02, was 187 vs 138).
5. Ported shadow-driver fixes into repo `build_clip.py`: drops scoped
   to the rendered range (full-chapter behavior unchanged), subtitle
   wrap 46→40→36→32 with the failing bid in the assert, intro-end
   hold rule, stale-opath delete kept (M21).
6. Fixed two bugs found by reading proof PNGs: `chapter_title`
   required granny voice so the header lost its title when b2
   flipped to verse (now: first block carrying Deva, any voice —
   ch01 safe, its numeral path ignores titles); verse glossary
   lookup folded whole mixed-script lines so b2's chant card lost
   IAST + literal (now `verse_match_key` on the Sanskrit half).
7. Landed the owner's chant-at-start order: removed b2→granny
   overrides ch02–22 (ch01 b2 is English, stays granny; ch01
   already opens on mangala chants). All 21 rebuilt green,
   b2=verse/verse verified per file. Approvals now stale (SHA
   changed) — republish + re-bless required before any render.
8. Rendered ch02 holds sheets, read all 6 with own eyes, filed
   `review/ch02/notes_round2.md`. Header level, b2 four layers,
   verse cards correct (b82 +IAST two-line source; b92/b127 bare
   Deva — not glossary terms, correct).

## The chunk method (canonical, documented in BUILD-NOTES)

Groups are the audio atoms (same-section same-voice, sha1
filenames — audio renders once, re-runs are cache hits). Chunks
are ranges of whole groups only (M6); ranges never end on an
owner drop group. Per chunk: storyboard gate → audio-cache check
(render missing groups first, Fish free) → build → proof pack
(`prove_clip.py`: boundary frames, mid-speech frames, contact
sheet, index, gate run, notes template) → eye read vs storyboard
+ Qwen taste (transcript corroborated) → notes filed → fix →
re-proof. Full chapter only concats proven chunks, then verify
+ golden-check + review-pack. `run_blocks.py` + `prove_clip.py`
+ `gate_storyboard.py` are repo scripts now, not /tmp shadows.

## Audit findings (all 22, estimates @150wpm)

Two diseases, both real: stuck single-term cards for minutes
(ch21 uttirna 8.5min, ch22 sivam 7.8, ch01 diksa 2.4 — ch01 is
loved, so estimates may overstate; measured gate decides);
body white 50–75% (ch08 50.7/64.8, ch20 63.8/93.5). ch02's 85s
white b52→b82 is correct-by-data: that stretch speaks English
argument (possibilities 2–4) with only the name Śiva, which was
never a glossary card term — no cue exists to fire. First-mention
cues + tone-break returns are the only hold changers; re-mentions
never re-fire (one-cue-per-block, PROCESS open delta).

## Open questions for the owner (nothing moves without answers)

Status 2026-11-04 close of session: storyboard routine complete
all 22 (gates, sheets read, proofs filed, packs republished).
Decided since: thumbnail intro-scoped (law+code), header optics
(137v138 measured), b2 chant all 21, H8 advisory, white
verified correct-by-data. Still open: re-bless 21 SHAs,
Deva citations ch14–22, impact disposal + 14 calls, paurusa
gloss + anyam timestamp, per-chapter art, ch01 ears, ch14–22
casting, L3/L4. Then the BUILD-NOTES "What's next" sequence.

Superseded detail (kept for the record): items 1–4 above are
decided — thumbnail intro-scoped, header optics measured,
b2 chants landed, H8 advisory, white verified correct-by-data.

1. Re-bless storyboards (b2 SHAs changed) + republish packs?
2. Header optics blessed?
3. 85s ch02 white: bless the argumentative white, re-fire term
   cards on re-mention (builder change), or place drops? Note:
   drops clear holds — they cannot fill white.
4. ch01 diksa 125s vs loved v3: is H8 60s too strict, or do
   stuck single cards need clearing after 60s?
5. Per-chapter art for ch02–22 (fallback shows ch01 art).
6. Ears on ch01 (seals golden); ch14–22 casting; Deva citations
   (M15/M23); L3/L4 signoff.

## Crisp + drops (the hold-and-release law, all refs in one place)

The visual engine is: she says it → Deva + IAST + final go up →
they hold → something later clears them. Two mechanisms clear:
the next cue supersedes (M11), or a deliberate release.

Crisp (GATES H2, VISUAL §2, GOLD-STANDARD §6, code `bed_after` in
`build_clip.py`): multi-line chants hold the verse card through a
2.8s bed, then boom white — 2.8 not 3.0, the tripwire that fired
past 3.0s is retired, verify hunts uncomposed silence past 10s
only. Singles get 0.6s and persist one block instead (no white).
Proven on ch01 b8–b10: +2.2s exactly, linger frame then clean
white with her next line lighting (`PROCESS_NOTES.md` crisp
section). Beds table (clip rhythm, canonical): 0.8 structural /
dialogue / section-end / long-pause, CRISP 2.8 multi-line chant,
0.6 verse single, 0.3 flow. `assemble_chapter.py` mp3 beds still
read 0.4/1.0 — open delta, clip table wins.

Drops (VISUAL §6, GOLD-STANDARD §7, GATES H7, code `_drop_at` +
`_drop_last` in `build_clip.py`, gate `H7 filed-vs-meta` in
`gate_visual.py`): owner-called `{bid: {pause, why}}` in
`drops_chNN.json` clears the active hold at that block's group
end and stretches the bed by pause — card through the last
spoken word, clean white with no subtitle across the pause,
next card after. Audio pauses exist only at group boundaries
(M6: groups are atomic — a non-final bid fails loud). Every
pause needs its why or it never renders. Filed: ch03 b11/b75,
ch04 b91/b123, ch05 (2), ch06 (2). They take effect on the next
video build of each chapter (03/04/05 post-batch re-runs, 06 on
its next build). Pauses stay proposed until heard.

## Gold inventory (what's golden, what's missing, what's stale)

Golden means sealed after owner ears against `golden.py`
tolerances (duration ±2s, cue order/drift, white ±5pp, cuts).
`golden/` is EMPTY — nothing sealed anywhere, both lanes.
Reference that plays golden's role until sealing: R2
`tantrasara/ch01_full_v3.mp4` (439s, 898 cuts, GOLD-STANDARD).
Its proof pack lives in-repo: `review/ch01/` (storyboard.md,
timeline.md, sheets, manifest) + `notes_round1.md` (self-review
with the four-layer stack proof) + `sheets_notes_round1.md` +
`qwen_final_pass4.json` (rescued from /tmp this session — taste
verdicts: karaoke-ahead uncorroborated, ṛ misread discarded,
dash fixed). Shiva preview proofs on R2 (`shiva/preview/`:
s01 mp3 + chant-card PNG + opening mp3) per SHIVA-INTAKE.
Missing: ears on ch01 (the seal), per-chapter art for ch02–22
(fallback shows ch01 art), title entries unconfirmed, L3/L4
finals, Qwen finals per chapter as they land, fresh republish
of review packs post-confirm (manifest SHAs predate the b2
flip), the `r2:.../golden/` prefixes. Stale, do-not-link: R2
root `ch01_full`, `_v2`, `ch1_opening…_v4`, `first_min*`,
`cards/*`, `ch02_firstmin/intro_frames`, `gateframes_round1`,
my `ch01_exemplary` (not v3-identical) and `ch03_p0*` parts;
local `finals/ch01_full.mp4` (pre-crisp) and
`finals/ch02_full.mp4` (pre-flip); `finals/ch03_full.mp4`
(VERIFIED current builders — good stock, pending b2 re-render).

## How to continue (the routine that would have prevented M24)

Storyboard → sheets → proof PNGs → read every frame against
GATES with notes per round → fix → re-proof → green → render
chunk → prove → verify → Qwen → ears → seal → upload `copyto`
+ HEAD → commit one concern + push same day. No "looks fine"
without attached frames + gate output + meta. Never trust a
stale mp4 (M1/M10). Never work around run_all (M25).
