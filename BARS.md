# BARS — absolute bars (from MISTAKES.md M1–M32 + 2026-11-05 crash triage)

Each bar is a numbered law with its mechanical enforcement. Learned the hard
way; encoded so no agent re-learns them. The gate is a proxy; the rule is
the law.

## Evidence (a file proves nothing about what made it)

1. One canonical name per deliverable (`chNN_full.mp4`); dated archive
   copies only; every link message names what changed + retires one stale
   key. Never mint a new R2 root key (M1/M27).
2. No ship without bound meta: storyboard + glossary SHAs + builder
   version + audio hashes + proof reviews travel with the file (M24).
   `copyto` exact keys, HEAD 200 + byte match (M7).
3. Model verdicts never gate: Qwen taste-only with transcript/waveform
   corroboration; timestamps past file length void the pass (M2). Whisper
   is content-only, never timing (PROCESS_NOTES).

## Judgment hygiene

4. Decide from census, never samples: full UNCAST dumps with frames (M9).
5. Re-read before every positional claim; storyboards move under you (M10).
6. A gate checks WHO speaks: voices-per-seat energy after every concat (M29).

## Script purity (display text)

7. No Devanagari glyph may reach the subtitle face from any path (M3).
   Verse subtitles render IAST, always.
8. Devanagari and roman never share a line; author's roman half IS the
   IAST line; karaoke remaps to visible words (M4/M16).
9. Folding is explicit table + NFD-strip, never NFD alone (M5).
10. Term cards render glossary citation Deva, never the folded key (M15).
    Deva enters ONLY by owner citation or verbatim extraction — never by
    transliteration, however checked (M23).
11. Verse blocks carry words only: digits/digit-danda clusters live in
    header refs (M17/M31 — numerals spelled for the aligner only).

## Atomicity

12. Groups are atomic (content hash); ranges never split a group (M6).
13. Duration math: assembly == bell + groups + beds; a mismatch means a
    wrong file got in — investigate, never adjust a constant (M8).
14. Newer cues win: spans clamp at the next cue start; coverage proves
    every cue got screen time (M11).

## Data discipline

15. Overrides are text-anchored, never bid-carried; remap proves UNCAST
    count + zero drift + absolute rules (M12/M18). Never touch production
    data without git status first; one chapter green before the next (M26).
16. Generators are scoped (`--only`) or they don't run post-approval;
    a lane-wide regen is a re-bless event (M13/M19).
17. Filename quirks resolve in exactly one place; gates never pass on
    empty inputs (M30).

## Failure loudness

18. Crashed aligns delete stale outputs before invoking node; staging
    verifies size + sha256 with retries (M21).
19. A stage that cannot prove its output stops the chapter with nonzero
    exit — never the run, never silently (M22).
20. Entry gates run before tokens burn: bundle, pack, source, gate,
    free-tier, storage, models resolvable.

## Physics (autonomy never overrides it)

21. Fleet launch pattern always: setsid + nohup + log in one instant call,
    aliveness verified in a separate call; never sleep/poll in the launch
    call (M20).
22. One video build at a time; the lock is code (pid-checked claim,
    family-safe, stale-inert), plus per-output locks; no shadow builders,
    ever — port fixes into the repo (M25/M28).

## Crash triage 2026-11-05 (new bars)

23. Align routing is size-aware with margin: >200 words take silence-split
    halves; a dead single-align falls back to chunked, never kills the
    build. OOM boundaries are pressure-dependent — never tune to the edge.
24. Audio renders max progress per attempt: per-group guards (timeout,
    mount-flake retries, receipt warn-and-keep), exit 1 while anything is
    missing so the driver retries and the cache heals.
25. No stage runs blind: every stage logs to its own file; the driver
    keeps evidence, never memory-only tails.
26. Crashed runs leak transients: the driver opens with an orphan reaper
    (anything unreferenced by a live lock or resume manifest is swept).
27. Local-disk flakes are real at 99%: preflight is a floor, and every
    filesystem read on the hot path retries.
28. Motion is justified like silence: every draw files {start, asset,
    complete frame, clear fade|cut, why} — unjustified motion never
    renders. Entry always fades in from white; clearing is fade to white
    over `fade` seconds (crisp-shaped) or an instant cut (drop-shaped).
    The complete frame shows the full image; progress is measured between
    two word onsets, never estimated. Frames are transient; mp4+meta+subs
    persist.
29. Staging law (Sanskrit hold, decide drop, blank, decide draw — never
    Sanskrit straight into draw): motion renders ONLY on white; chant,
    cue, persist and thumbnail cards always win. A draw/clip must START
    on a white word (asserted, fail loud). The blank is our silence.
30. Holds release: a persist clears to white 60s after its chant onset
    unless superseded (max hold ~60s, owner call 2026-11-05); completed
    draws clear the same way. Newer persists win over older (cue-clamp
    mirror M11) — a fresh chant re-covers, never flashes one frame under
    a stale hold. Re-mentions re-fire, so live cards survive.
29. Overlay clips play muted on the mini canvas (centered 1280x660, above
    subtitles) between two onsets, then hold their last frame like a
    persist. Filed like draws {start, asset mp4, complete, clear, why};
    used sparingly, for effect. The mix stays ours — clip audio never
    renders. Pre-rendered once (scaled, looped/trimmed, 15fps); frames
    transient like all motion.
