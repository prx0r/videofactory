# VISUAL CANON — Tantrasara explained (locked 2026-11-03, owner-confirmed)

One screen language for all 22 chapters. `holds.py` is the single
implementation (sheets and video share it); this file is the law it
implements. Change only by owner call, same commit as the code.

## Canvas
- 1920×1080, 30fps, libx264 + AAC. White ground `#FFFFFF`, ink `#17140F`,
  gloss grey `#CFC9BE`.
- Subtitle safe zone: y=860, max 2 lines. No card element may enter the
  subtitle zone or touch frame edges — collisions fail the render.

## Type stack (three faces, no others)
- Devanagari: Tiro Devanagari Sanskrit Regular. Verse 84pt, wrapped 64pt.
- Gloss: Cormorant Garamond Italic 40, grey. One line under the Deva.
- Subtitles: Cormorant Garamond Medium 46 → 40 if 3 lines threaten.
   Blocks that cannot fit two lines at any readable size show a
   two-line window around the spoken word instead (owner call
   2026-11-04) — every word still appears with karaoke over time.
   Ink = lit (spoken), grey = unlit. Verse subtitles in IAST transliteration
  Ink = lit (spoken), grey = unlit. Verse subtitles in IAST transliteration
  (the face owns no Devanagari glyphs); narration subtitles verbatim.

## Cards (owner-confirmed 2026-11-03: term cards as now, ~20% white target)
1. **Thumbnail + chapter numeral** — frame 0 through the intro, clearing
   at the first tone break (section break, long-pause beat, dialogue
   entry). Verse cards take over at chants whenever they come. Fitted above
   subtitle zone, never fullscreen-bleed. ch01 shows the thumbnail alone
   (blessed reference, never touched); ch02+ carry the chapter numeral
   top-right in house figure type (shared `intro_hold`, one code path for
   sheets and video).
2. **Verse** — Devanagari ONLY (subtitles already carry the romanised —
   owner call 2026-11-04). Up the moment chanting starts and held
   until the next Sanskrit word (next cue or chant) or the next tone
   break, whichever comes first (owner call 2026-11-04 — no chant
   dies into dead air); then boom white.
   The 2.8s crisp bed still breathes under multi-line chants
   (2.8 not 3.0: our own dead-air tripwire fires past 3.0s). Whole-chant T1 literal + L3 final
   tried and reverted same day (`mine_verse_gloss.py` output parked proposed
   in `verse_gloss_chNN.json`). Max 3 Deva line-pairs per hold. Single-word
   glossed chants     carry all three term layers (see 5).
   Up the moment chanting starts, clears the instant speech resumes. Max 3
   Deva line-pairs per hold. Single-word glossed chants carry all three term
   layers (see 5).
3. **Term** — three layers, closest to furthest from the Sanskrit: Devanagari
   headword (ink, citation form from the glossary — never rebuilt from the
   folded key) + IAST romanised (lightest grey, same onset) +
   final English gloss (darkest grey). Pops the instant she says
   the word; holds until the next cue or tone break (newer cue always
   supersedes). Only `confirmed` glossary terms render — `proposed` plays
   over white. (Literal morphemes parked per owner call 2026-11-04 — ch01 v3
   shipped three layers and that is the house look.) Single Sanskrit words stay with granny + term card; the
   verse voice is multi-line passages only.
4. **List engine** — count decides the shape, one standard Sanskrit size
   everywhere (Deva 84, locked 2026-11-04; IAST 32/28, literal 28/24, final
   40/36 by slot). One centered; two side by side; three in a row when they
   fit else triangle (apex + two below); four the corners; five corners plus
   middle (newest middle, earlier four in arrival order); past five the
   window slides. Every member carries all three term layers. Runs trigger
   on 2+ cues with no event gap between them. Every card asserts
   subtitle-zone and pairwise non-overlap — trips fail the build.
5. **Single-word chant persist** — a lone glossed chant (Aṇu., Svātantrya.)
   renders Deva + gloss underneath like a term card and stays up through
   the directly following block, then white. Cues always win over persist.
6. **Drops** — an owner call in `drops_chNN.json` (`{bid: {pause}}`) clears
   whatever card is up at that block's group end and stretches the bed by
   pause seconds: hold through the last spoken word, clean white with no
   subtitle across the pause, next card after. Audio pauses only exist at
   group boundaries (M6) — a non-final bid fails loud. Long white holds
   are legitimate dramatic holds, never dead air (the 3s tripwire is gone;
   verify only hunts uncomposed silence past 10s).
6. **Title / figure** — spoken titles stay spoken; no title cards in video.
   Figures (rare) render large numeral + short caption.
7. **White** — the default. Returns at every tone break, section break,
   long-pause beat, dialogue entry. House target ≈ 20% white per chapter;
   builds print COVERAGE and fail over 85% white (60s+ clips).

## Sanskrit breakdowns (owner call 2026-11-03)
Breakdown = the term card: full compound in Devanagari + one gloss line.
No compound-splitting, no interlinear verse gloss, no IAST on cards.
If a term needs parts explained, the narration says it; the card stays whole.

## Voices on screen (unchanged)
Granny narrates; man objects and dialogues at 75%; verse chants. Cards are
voiceless — they anchor what is heard, never add text of their own.

## Proof (every clip, no skipping)
Pull frames at: chant start, mid-verse, first term pop, a rapid-fire cue
pair, a dialogue turn, a tone-break return to white. Read each: right card,
right subtitle, karaoke on the spoken word, no tofu, no overflow, no
subtitle-zone collision. Then Whisper head-check (words present, not timing),
then Qwen taste-only, then owner ears.
