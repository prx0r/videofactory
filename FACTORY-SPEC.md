# FACTORY-SPEC — video factory (saved 2026-11-05, owner-ordered)

The video factory renders teaching series (tantrasara, shiva, future lanes)
from frozen storyboards to sealed mp4s. It changes no authorial text, casting
call, translation, owner decision, or approval. The running system in
`~/tantrasara` stays frozen until this factory proves parity; nothing here
renders production until then.

## 0. Position in the larger system

Translation-work is upstream (T1/L2/L3/L4 feed card layers through
versioned, sha-pinned drops only — never hand-copied strings). This factory
is the middle (storyboards to sealed mp4s). The site is downstream
(chunks, corpus, receipts). New series plug in as lanes (the shiva
12-line `lane_for` precedent), never forks. Lane contract: glossary/verse/
assets/thumbbox/numeral routing, R2 prefix, intake log, parametrized render
paths.

## 1. Layer stack (every layer: purpose, shape, producer, validator, gate)

SOURCE (sha-pinned chapters; split+cleanup idempotent, `--only`-scoped;
blanks intact; debris to meta; Deva-letter voices, digits never do) →
BLOCKS (`{id, section, type, voice, text, directed}`; fixed casting order;
per-bid forcing, unknown bids fail closed; gate 0/0) →
DIRECTION (versioned schema; v1 canonical now; S2 `[break]`/`[long-break]`
migration versioned with byte-proof + re-voice cost; tags prefix-only,
audit-proven, cap 3, never reach the aligner) →
GLOSSARY (citation Deva + IAST + literal + final, all proposed until
confirmed; folded keys lookup-only; confirmed-only on video) →
APPROVAL (owner act pinning storyboard + glossary SHAs + builder version) →
AUDIO (content-hash groups `sha1(voice|directed-text)`; receipts; human
phonemes same hash path, -21dB/-1dB; free-tier pin; probes before renders) →
ALIGN (word-onset rows, 1:1 asserted, mean ≥0.85, gaps-to-prior;
200-threshold routing + chunked fallback as pure tested functions) →
HOLDS/VIDEO (single-source holds; one clip-rhythm bed table; coverage
printed) → VERIFY/PROOF (geometry, levels, 10s-silence, whisper
subsequence, motion, voices-per-seat) → SHIP (canonical names, `copyto` +
HEAD, packs + sealed videos only, stale-key retirement) →
GOLDEN (duration ±2s, cue order/drift, white ±5pp, cuts).

## 2. Audio-stage law

Pure tested grouping (same-section same-voice; none skipped; opener
asset-copied; phoneme singletons carved by the shared rule; drops split
identically everywhere). Cache hit = size + sha256. Receipts append-only.
Probes before renders (whisper for English-dominant; owner ears for
Sanskrit/punctuation — garbling encoded as rule). Execution: per-group
exception guards, all subprocess calls time-bounded, mount writes retried,
max progress per attempt, exit 1 while anything is missing.

## 3. Storyboard-stage law

Fixed casting order with edge fixtures (shout-guard, digit-tokens,
mixed-script, Abhinav-man vs owner override — owner wins, recorded as
data). Overrides text-anchored with the three-part proof (UNCAST count,
zero-drift audit, absolute rules). Remap-by-identity is one shared library
function.

## 4. Absolute bars (BARS.md — each M-number mechanically enforced)

Naming/evidence (M1/M24/M27); judgment hygiene (M2/Qwen-taste-only, M9
census, M10 re-read, M29 who-speaks); script purity (M3/M4/M16, M5 fold
table, M15 citation-Deva, M23 no machine Deva); atomicity (M6 ranges,
M8 duration math, M11 cue clamping); data discipline (M12/M18/M26 remap
law, M13/M19 scoping, M30 single normalization); failure loudness (M21
stale-output deletion + sha staging, M22 nonzero exits, M31 numerals);
physics (M20 fleet launch, M25/M28 lock-as-code + per-output locks);
tonight (orphan reaper, per-stage logs, disk-flake retries, 200-threshold
+ chunked fallback, audio guards).

## 5. Verbatim lines, compiled

RUNTIME routine = driver state machine (blocks → edits → PNG proofs →
perfect render → Qwen-vs-beats final). Self-review loop = per-part review
record with PENDING_REVIEW stop (waived for byte-identical rebuilds).
Dumb-render contract = builder base class (PASS/FAIL, never decide).
Stop rule = red-state handler (halt chapter, re-freeze from step 1).
Autonomy contract = permissions table (PERMISSIONS.md): agent does
everything gates decide; owner-only capabilities requested per chapter.
Gospel amendments are dated, owner-signed, same-commit-as-code.

## 6. Strictness

One `check.py`: exit 0 = canonical, else failing step named. Versioned
schemas with sync check. Preflight before tokens (disk, lock, SHAs, V5,
audio cache, keys, models resolvable). No approval, no render. One
concern per commit. Open deltas tracked as gated gaps.

## 7. Migration (strangler, no big bang)

Schemas + contract + CI first (additive). Builders ported one at a time
with output-parity proofs vs frozen master builds. Master stays live
until parity. Codex durable pieces kept (schemas, tests, sha staging);
its pre-crash assumptions (300-threshold, unguarded audio) superseded by
proven fixes, ported onto the refactor.
