# RUNTIME — the owner's words (verbatim gospel, 2026-11-04)

> ok then we need to have some validation pass where you yourself think
> about what i will say, review the png and see for yourself what is good
> or bad, document notes then fix, then iterate like this until we pass
> some binary criteria.. yes we need a prx0r/qprivately type gate for the
> render stage like are the verse visuals like this, does each sanskrit
> syllable have the romanised and gloss etc with the colours etc just all
> the rules we have formalised in a canonical list you can then use int
> hevalidation review , we should have all the rules for this already so
> just get them in one place, make them binary so you cant cheat then
> basically the routine is that after we have got all the chapters
> organised in blocks, made edits for fish tts etc timings all teh editing
> and you are happy, tehn you can start the storyboard phases where u
> render png map all the timings who speaking what ensuring the karoke is
> all on point. then essentially byt the time u render it should come out
> perfect as either full chapter mp4 or actually iguess probably smarter to
> have by block mp4 ? hmm anyway endpoint is basically each chapter is a
> fully rendered perfect timed mp4.. we can then do a final pass with qwen
> omni to compare vs the storyboard beats and transcript to see if all the
> timings match and audio is on point, no garbled devangari etc all the
> little niggles we can create a script for qwen omni to look out for ..
> ok this is GOLD ssave exatly these words as the runtime for the whole
> thing they are gospel and northstar add it to agents .md ensureevery
> agent reads this and now work autonomsuly making exactly what iv said in
> data and processes

## What this means, built (same commit family, no drift)

- Self-review loop: machine renders PNGs, reads them against the binary
  gate list, writes good/bad notes, fixes, re-renders — iterates to green.
- The gate (`GATES.md`): every formalised visual rule as a binary
  pass/fail. No judgment calls at gate time.
- Routine: blocks → Fish/TTS edits + timings → storyboard phase (PNG
  renders, timing maps, speaker check, karaoke proof) → render comes out
  perfect because there is nothing left to decide.
- Endpoint: each chapter a fully rendered, perfectly timed mp4. Built as
  one chapter mp4 from block-aligned segments (segments are the review
  unit; the chapter mp4 is the ship unit — concat demuxer lessons (M8)
  make block-mp4 assembly the riskier path, so blocks render as PNG +
  timing proofs and the mp4 muxes once, whole).
- Final pass: Qwen omni script (`qwen_final.py`) compares the render
  against storyboard beats + transcript: timings match, audio on point,
  no garbled Devanagari, all filed niggles.
