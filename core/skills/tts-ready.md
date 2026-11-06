# tts-ready (needs owner — probe, reword, rebuild)

Symptom: a voiced block Fish cannot deliver faithfully — leading junk
(`-yoḥ`, `-āt` suffix fragments: the TTS reads punctuation, not
grammar), a lone diacritic block (garbage audio), an embedded label
line (`TRANSLITERATION` / `ORIGINAL SANSKRIT` / source-note inside a
spoken block — split to label/meta + rebuild), a URL, markdown, a
citation tail, or a read-more/keep-reading trailer.

Diagnosis (`core/builders/check_canon.py`, mechanical only, shiva-only
like its sibling): every finding is a shape match, never taste.
Explicitly NOT flagged: `Next:` trailers (canon outros, owner-blessed),
enumeration runs (short fragments with no terminal — list-stack cards
own that patter), colon-ender beats and dash handoffs (direction
devices), `+`/`^` spellings (`Sound + touch`, `10^17` — Fish says
"plus"/"to the power", verified desired), danda/period doubling.
Two suffix fragments (s65 b11, s72 b13) are the entire current backlog —
morphology teaching that needs an explicit voicing decision
(reword to "the ending yoḥ" vs accept Fish's reading), proven by
`probe_rough.py` (cheap Fish probe, whisper/ears dispose) before any
render burns tokens.

Fix: probe the exact block text, owner disposes (reword / accept /
restyle), rebuild if the text changed, re-run checker to GREEN.
Preservation law holds: punctuation/whitespace/label fixes keep ≥99%
by construction; report the word-multiset overlap for any reword.
