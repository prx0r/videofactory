# verse-term-unheld (auto-fixed in code)

Symptom: verse voice chants a glossary term (Devanagari or IAST, e.g.
`Śaktipāta.`, `आगमप्रामाण्य`) but no term card appears; granny continues
over white or a stale hold while the just-chanted term never shows.

Diagnosis: cue generation watched narration/dialogue only, and Devanagari
was folded without transliteration so it never matched the ASCII key.
`_is_single_glossed_verse` existed but was never called (dead code).

Fix (applied, same commit as this skill):
- `build_clip.py`: verse blocks fire cues; Devanagari words go
  Devanagari→IAST→fold before matching. Verse card still shows DURING the
  chant; the term cue surfaces after.
- `gate_storyboard.py` H8, `holds_timeline.py`, `require_list_geometry`:
  same verse-inclusive matching.
- `hold_img`/`hold_kind`: lone glossed chant (anu-case, skill
  tantrasara-holds) renders as a TERM hold with all four layers and holds
  through following narration.

Process note: found via `scan_holds.py` reasoning
(`verse bX chants Y but no cue fired (BUG)`). Tantrasara precedent:
BUILD-NOTES persist/anu-case, skill tantrasara-holds single-word rule.
Re-run `scan_holds.py` — verse-term holds must list (e.g. ch15 17, ch21 38).
