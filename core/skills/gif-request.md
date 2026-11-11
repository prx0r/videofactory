# gif-request (how to order a new GIF from the maker queue)

ChatGPT owns the GIF queue; this skill is the order form. A good request
comes back as a loopable emblem; a vague one comes back as decoration.
Read gif-choose first — only recurrent motifs qualify.

## The maker envelope (every item, no exceptions)

GIF89a loop, 12 frames, ~310x414 portrait or square, 0.5–1.5 MB,
pure-white background, blue-ink pencil-engraving line, minimal, arty,
NO text, seamless loop (last frame flows into first). One moving element,
rest still. Slugs lowercase-hyphenated (`fire.gif`, never `Fire Final.gif`).
Full-bleed scenes (chip-shop, ocean, night-bus) are exceptions, not the
rule: they need a white-mat or an explicit owner exception recorded on
the entry.

## The brief (all four lines, or it is not a request)

- **motif**: the image in one line ("A single upright flame, steady").
- **why**: the recurrence that earns it, with counts
  ("27x chant-image across all 78 sutras").
- **lane beats**: which units and which bids will play it
  (cite `process/gif-placements.md` hits).
- **watch**: what moves in the loop in one line
  ("Flames take the pile; the center holds").

File the brief as a `wanted` entry in `core/art_bank/motion.json`
(id, motif, why, used_in, status, brief) and add it to the lane section
of `core/art_bank/chatgpt-queue.md`. Same commit, never apart: a queue
line without a bank entry is a rumour.

## On arrival (the checklist, in order)

1. Visually review it (contact sheet, mid-motion frame): motif match,
   white ground, no text, seamless loop, one moving element.
2. Audit it: 12 frames, even delays (uneven judders at 2x), rim mean
   >225 (white-rim gate), sizes sane. Record any exception (full-bleed,
   text-as-image like the Malini letters) on the entry.
3. Name it: `motion/<slug>.gif`, matching the wanted id exactly.
   Never bank a `ChatGPT GIF ... PM` filename — rename on arrival or the
   bank rots. Verify no stale twin exists (byte-compare; same bytes under
   two names is one emblem, not two — keep one, revert the other to wanted).
4. Flip the entry: status `banked-described` + depicts/means/use/watch +
   file + used_in units. Depicts the artifact, means the doctrine, use the
   lane beats, watch the loop.
5. Regenerate `chatgpt-queue.md` counts, run `vf_motion` to confirm, commit
   bank + queue together, push so the maker sees the live list.

## Speeds and ramps

Request the emblem at native pace. Playback speed (2x, reverse, ramps like
0.25→4) is a render decision in vf_seamless_draw, never a property of the
file. Do not ask the maker for "a slow version" — ask for one good loop.

## Variants (same motif, different telling)

When several images serve one motif, bank each under its own slug with
`variant_of` (base id) and `variant_when` (one line: when to use this one
over the base, e.g. "use when the burst must be geological and outer").
Inherit the base's `used_in` unless a variant genuinely serves different
beats. The MCP surfaces variant fields on every query — choosing between
three skies for one ocean is the whole point of the bank.
