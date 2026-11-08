# av-sync (auto: check_avsync + trimmed remux)

Symptom: `check_avsync.py` reports AVSYNC FAIL/WARN — audio stream
duration differs from video past tolerance (standard 80ms, Spotify
strict 10ms). Typical case: AAC audio ~28ms longer than h264 video
(e.g. ch01 31.3ms, ch22 27.9ms, mega ~28ms). Strict distributors
(Spotify) reject any delta > 0 even though the gap is inaudible.

Diagnosis: AAC encoder padding (1024 samples @48kHz ≈ 21ms plus
container priming) — not a content defect. ffprobe stream durations
are the evidence; container duration vs stream duration can differ
slightly in some readers, so compare stream-to-stream, never container.
A mid-download truncated upload can also look like a mismatch — rule
that out first (byte-verify local vs remote size + HEAD).

Fix (render box only, Rule 8: never ffmpeg-encode on the hub;
ffprobe read-only is fine anywhere):
`VDUR=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=nw=1:nk=1 <clip>)`
`ffmpeg -y -v error -i <clip> -c copy -t "$VDUR" <clip-spotify.mp4>`
lossless stream copy, trims audio to video length exactly. Re-run
`check_avsync.py <clip-spotify.mp4> --spotify` — expect <=10ms PASS.
Proven 2026-11-08 on tantrasara mega (19.3h concat of ch01-22).

Process note: run `check_avsync.py` on every final plus any mega/concat
before publish; standard outputs PASS with the AAC note recorded,
Spotify-target outputs must pass --spotify before upload.
