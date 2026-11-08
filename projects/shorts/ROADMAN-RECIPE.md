# Roady G recipe (repeatable — owner-blessed 2026-11-08)

## Inputs
Shorts storyboard JSON (`projects/shorts/storyboards/shorts_*.json`):
lines with `directed` (roadman reword), `maps_to` source bids (C2 rule),
`voice: roadman`. Granny minute first, Roady off her, handoff links.

## Voice
Fish `fish-audio/s2.1-pro-free`, seat roadman
`e64e97ef91304e2894cd72ff03b86d97` (free-only law holds).

## Render (per line, then stitch)
1. One TTS call per line: `tts_line.py "<directed>" lNN.wav 1.0 <voice-id>`
   (hub OK — API call, not encode; receipts in batch logs).
2. Stitch in plain code with INTEGER frame math only:
   `gap = rate * ch * sw * 35 // 100` (~0.35s breaths). Float seconds
   round to odd bytes and corrupt the tail (Bar 33).
3. Verify before upload: total bytes even, header size == data size,
   clean `ffmpeg -i file -f null -` decode end to end.
4. Publish: `rclone copyto` + `lsl` size match + HEAD `Content-Length`
   match. Key ends `.wav` for honest content type.

## Video assembly (server2, Rule 8)
Vertical cards per line (emblem + caption in safe zones) → per-line mp4
→ concat `-c copy` → atrim-exact audio to video duration (av-sync law
≤10ms) → verify → publish. See docs/SHORTS.md for geometry.
