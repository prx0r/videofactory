# missing-audio (auto: render_chapter)

Symptom: `require_audio_complete` fails:
`missing audio render for bX..bY` (ch18 b340 precedent: dialogue
`“Can I take Sundays off?”` had no wav, video died mid-range).

Diagnosis: group wav absent on the lane volume (content-hash path
`sha1(voice|directed-text)` missed — new/edited block, or narrow miss).

Fix: `render_chapter.py <storyboard>` for the unit (free-tier pin
verified by gate, per-group exception guards, mount retries). Re-run
`require_audio_complete` — 0 missing before video. No data edit needed.

Process note: gate names the exact group range. ch18 currently reports 3
missing groups; all other 14-22 report 0 missing.
