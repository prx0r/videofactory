# markdown-speech (voiced text must be speakable)

TTS speaks the `directed` field verbatim and subtitles print it — markdown
in a voiced block is heard and seen by real people. Shipped lanes were
clean by luck (their chapters never used `###` or `**`); nibbana carried
226 spoken hash-headers, 538 asterisk readings and 2 table readings, and
paratrishika carried thousands more. Nothing caught it: the builder only
stripped `#` levels 1–2, and the validator never looked at markup at all.

## The rule

Voiced blocks (granny/man/verse) contain prose, never markdown. Headers of
any depth, bold/italic markers, list bullets and HTML breaks are stripped
at build by `speak_clean()`; tables can never be stripped by rule (prose
needs a human), so `validate()` ERRORS on pipes in voiced text and the
unit stays red until someone hand-writes the sentences.

## Fixing a board (vf_speakclean does exactly this)

1. `vf_speakcheck` first: counts per hazard (hashheads/emphasis/tables)
   per unit. Zero everywhere or stop.
2. Strip: `speak_clean()` on voiced `text` + `directed` (direction tags
   `[short pause]` pass through untouched; voice-none blocks keep raw
   provenance text).
3. Tables by hand: `Term: gloss.` sentences, one per row, tags kept up
   front. Two-column term/gloss tables convert 1:1; anything else gets
   real sentences, never pipe-deletion.
4. Re-run: residue audit must read zero, `validate_bundle` must pass,
   draws/clips re-validate (bids never change, so they do).
5. Pre-approval boards only: text edits move SHAs, which is free before
   owner approval and forbidden after. Never clean an approved unit
   without a fresh approval.

## Regression lock

`build()` cleans every voiced block, so future rebuilds from chapters
cannot reintroduce this class. `validate()` errors on residue, so the
gate stays red instead of shipping asterisks. Tests pin both in
`tests/test_factory_contract.py::TestSpeakClean`.
