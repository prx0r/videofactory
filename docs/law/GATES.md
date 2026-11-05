# GATES — binary render-stage checklist (no cheating)

Every line is pass/fail. Machine lines run in `gate_visual.py`; eye lines
are read off proof PNGs with good/bad notes filed per round. A chapter
renders only when every applicable line passes. Owner calls can change a
rule — same commit as the code, never a wave-through.

## Canvas and type (machine + eye)

- V1 canvas is 1920x1080, 30fps, one video + one audio stream. [machine]
- V2 Sanskrit Deva is 84 everywhere it stands alone; 64 only as the
  single wrap-down step. No 44s, no other sizes, middle and corners
  alike. [eye on PNGs + asserts at build]
- V3 verse cards are Devanagari ONLY (subtitles carry the romanised);
  IAST lines live on term cards and the canonical title. No bare Deva
  anywhere else. [eye]
- V4 every confirmed term carries final (darkest grey). Literals live in
  data as proposed only — never on screen (owner call 2026-11-04, ch01 v3
  standard). Proposed layers never render in
  video. [machine: video dict filter] [eye: ramp order top to bottom]
- V5 Deva is the glossary citation form, never rebuilt from the folded
  key (M15: ś/ṣ survive). [machine: every confirmed term has non-empty
  deva; spot eye]
- V6 every layer centered under the Sanskrit above it. Exception, locked:
  canonical header is title top-left + numeral top-right on one baseline.
  [eye]
- V7 brackets not parens in literals. [machine: scan, no `(` `)` in
  literal fields]
- V8 no full transliteration blocks on cards — per-term IAST lines only.
  [eye]

## Holds and timing (machine + eye)

- H1 thumbnail frame 0 through intro end (first tone break: section
  break, long-pause beat, or dialogue entry — never the first chant).
  ch01 clean; ch02+ numeral (zero padded) + canonical title, title ink
  optically level with the numeral. [machine: coverage thumbnail > 0]
  [eye]
- H2 verse cards while chanting and held until the next Sanskrit
  word (next cue or chant onset) or the next tone break, whichever
  comes first — no chant dies into dead air; the 2.8s crisp bed
  still breathes under multi-line chants, 0.6 after singles. Lone
  glossed chants keep all term layers. Cues always win over
  persist. [machine: persist spans in build log match verse-block
  count] [eye: card holds to the next Sanskrit, then clean white]
- H3 list runs are 2+ cues with no event gap; shape follows count
  (1 centered, 2 side by side, 3 row-or-triangle, 4 corners, 5 corners +
  middle, window slides past five). [machine: render_meta cues order
  matches storyboard run scan] [eye: shape per accumulation step]
- H4 white appears only at section breaks, long-pause beats, dialogue
  entries, post-chant clearing and unconfirmed stretches. White ≤ 85%
  past 60s. [machine: render_meta]
- H5 subtitles carry no Devanagari glyph anywhere, any voice. [machine:
  scan built subtitle words] [eye: no tofu boxes]
- H6 karaoke lights the spoken word at its onset; gaps belong to the
  prior word; 1:1 word mapping asserted at build. [machine: build assert
  + whisper subsequence ≥ 0.35 per block] [eye: two mid-speech frames]
- H7 every filed drop applied in the render with its pause, every one
  justified (pause > 0, non-empty why). Unjustified silence never
  renders. [machine: filed-vs-meta diff]
- H8 no visual static past 60s (advisory, never alone fails the render):
  a hold change, cue, break, or chant lands within 60s of the last,
  every minute of every chapter — where no Sanskrit is spoken, none
  can show. Estimates at the storyboard gate, measured onsets at the
  video gate. [machine: report gaps] [eye]

## Audio and delivery (machine)

- A1 MMS mean ≥ 0.85 per group, zero non-monotonic, row counts match.
- A2 assembly duration equals sum of parts; no uncomposed silence past
  10s (deliberate holds exempt by design); levels
  in band (mean -32..-12dB, peak > -8dB); motion ≥ 70% distinct frames.
- A3 golden match: duration ±2s, same cue order, cue drift ±3s, white
  ±5pp, cuts drift. First blessed render seals it.
- A4 Fish s2.1-pro-free only; receipts log every call; re-runs are
  content-hash cache hits.

## Data gates (machine)

- D1 storyboard green: 0 errors, 0 warnings. UNCAST never defaults.
- D2 approval file exists with matching storyboard + glossary SHAs, or no
  render runs.
- D3 glossary keys are folded ASCII; confirmed terms carry deva + gloss;
  video literal requires its own confirmed status.

## The routine (self-review loop)

1. Render the segment (group-aligned bids) + proof PNGs (every hold
   change + two mid-speech frames).
2. Run `gate_visual.py` (machine lines). Fix reds, never waive.
3. Read the PNGs against the eye lines. File good/bad notes per frame
   (`review/chNN/notes_roundN.md`), fix, re-render.
4. Iterate to all-green. Then full render → `verify_clip.py` → Qwen final
   (`qwen_final.py`: beats vs transcript, timings, tofu, niggles) →
   owner ears → seal golden → commit + push.
