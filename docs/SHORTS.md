# Shorts — vertical distillations (spec, owner-ordered 2026-11-08)

## Thesis
Hours of long-form become 1–2 minute verticals. No new recording: audio
is sliced verbatim from content-hash group wavs, pictures from the GIF
and draw banks. A short is a re-cut, never a re-render.

## Format (hardcoded from 2026 platform specs)
1080x1920 9:16, 30fps, H.264 + AAC stereo, ~8 Mbps MP4. Target 60s
(3 min is the ceiling, never the target; over-1-min + claimed material
gets blocked, ours is original throughout). Safe zone: top 288, bottom
672, left 48, right 192. Emblem max 440 wide centered ~y690-960; voice
tag y620; captions from y1210 (never the bottom third). Hook text
y680-750. First frame starts on the subject. A/V strict ≤10ms
(atrim-exact at mux, per av-sync law).

## Selection rubric (scored, then owner picks)
1. Self-contained exchanges: man-voice runs of 3+ beats with setup, turn,
   and button (e.g. receipt bit, salt bit, Sanskrit-on-Tuesday).
2. Verse + gloss utterances: 15–30 second jewels, chant plus meaning.
3. Comic rants: caps runs that survive without context.
4. Openers and closers: cold opens, final stitches.
5. Owner picks override everything above.
Replayability = short + complete + funny-or-profound. Starter mine
surfaced receipt/salt/Tuesday-class bits unprompted.

## Pipeline (new builder, frozen-proof required)
shorts cutter: select spans → slice group wavs (no TTS) → vertical
compose (emblem + karaoke) → verify adapted to 9:16 → publish pack.
Mirrors the main line minus recording; ears stay mandatory, seals stay
per-short. Naming: shorts_<lane>_<unit>_<n>.mp4.

## Roadman cut (owner-ordered voice)
Shorts voice the skeptic in roadman: Fish voice
`e64e97ef91304e2894cd72ff03b86d97` on `s2.1-pro-free` (free-only law
holds — voice ID is data, model string stays `-free`). Granny stays
posh narrator; the comedy is the contrast. Man-dialogue exchanges,
caps rants, and wrong-view bits go roadman; verse and narration stay
house voices. Candidate status until a test render blesses it — wire
into lane voices only after ears pass. Roady G = roadman persona;
Big G = granny herself in third person.

## Roady-to-Big-G handoff (owner style bible 2026-11-08)
Two-minute shape. First 60 seconds: Roady G in roadman, META — he
explains the GIF on screen ("so boom, look at dis stunning AI generated
gif right, there's the sun and the beautiful clouds, basically it's a
metaphor innit, you are the sun of consciousness always there and
shining, sometimes the clouds get in the way but the sun's always there
you know what I mean"). Then Big G (granny) enters, affectionately
condescending: isn't he sweet, absolutely right Roady G, but let Big G
take it from here — and explains the SAME thing straight (the exact
video content, condensed to 60 seconds). Bait (charm) then handoff
(substance). Workflow runs backwards: condense granny to 60s first,
then generate Roady's 60s off it, then link with the handoff line.
## Volume
Pilot 3–5 shorts per long unit (tantrasara chapters, early shiva units
first — several already run near shorts length). Scale to hundreds only
after the pilot's retention proves the rubric.
