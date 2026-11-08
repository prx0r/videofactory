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

## Roady frame (owner direction 2026-11-08)
Roady reacts to the GIF as if seeing it for the first time, talking to
his mate — personal stories allowed to land the image. Each 60 seconds
is one thing: spanda, prakasa, what is Siva? Source of truth for the
voice: translation-work `paramarthasara/ROADMAN-v1.DRAFT.json` (all 105
verses in roadman, machine draft pending owner review — register bans
cap/fr/bussin/vibe/delulu/lowkey).

## Roady grammar (owner thesis 2026-11-08 — Tandava cut)
- GIF AS BIG AS POSSIBLE. The picture fills the frame; captions ride
  over its quiet zones. Small-emblem minimalism is for the long-form
  cards, not for Roady.
- ALWAYS ABOUT THE GIF ON SCREEN. Every line points at the picture.
  New GIF pops up first, Roady reacts second: "ok we got a new one" —
  then he interprets it live (e.g. cinema GIF up BEFORE any film talk).
- MADE-UP WORDS, TRUE DOCTRINE. He mints words freely ("syllogical")
  and is always accidentally stating the absolute truth. That gap IS
  the comedy — wrong words, right Dharma, every time.
- CLOSING TAG. After Big G takes over, Roady gets the last mutter:
  "nah she's proper rude innit. Sounds kinda leng tho." He watches
  the screen with the viewer throughout.
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
## Formats (from characters2: bait + standup-60)
BAIT: the viewer must not know for the first twenty seconds whether
this is comedy or teaching — hook reads as pure joke, turn reveals the
doctrine underneath (or reverse: sincere teaching, comic rug-pull).
STANDUP-60: setup installs a reading, punch replaces it using only
material already on screen; three beats max (two same-kind, turn on
the third); punch word last, nothing after it. Roady rambles, Big G
deadpans — never both at once.

## Automation (as good as the video line)
Mine with `vf_shorts_mine` (verse spans, exchanges, closers, scored).
Write picks as `projects/shorts/storyboards/<name>.json`: verbatim lines
+ maps_to source bids + emblem + 9:16 format block. Derive Roady versions
with `vf_roady_pack` (granny lines, GIF options, SO/LM triples, register)
then handcraft the reword one at a time — currently at shorts 11–20 of
the 50, Roady derivations to follow the same order. Topics live in
`projects/shorts/index.json` (no-repeat law enforced there).

## Volume
Pilot 3–5 shorts per long unit (tantrasara chapters, early shiva units
first — several already run near shorts length). Scale to hundreds only
after the pilot's retention proves the rubric.
