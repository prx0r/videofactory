# Autonomous factory handover

This describes the executable handoff added on 2026-11-04. Read it with
`RUNTIME.md`, `GATES.md`, `STANDARD.md`, and the dated history in
`MISTAKES.md`. It changes no authorial text, casting call, translation,
owner decision, or approval. When older status prose conflicts with current
artifacts, run the audit below; do not infer a blessing from an old log.

## What the audit actually found

At master commit `8d2f9ea`, all 100 checked-in storyboards and glossaries
(22 Tantrasāra, 78 Śiva) passed the new structural checks. A temporary
rebuild of all 100 also reproduced the saved title and blocks from the
source and overrides. This local source comparison ignored missing external
kit assets; production does not ignore them.

At that same commit, the 13 Tantrasāra approvals for ch01–13 matched the
storyboard and glossary bytes. Ch14–22 approvals were stale, and no Śiva
render approvals were present. All 100 old review manifests lack the new
view hashes, so the production gate requires the packs to be republished;
this does not change the underlying approvals. These are observations, not standing
permissions. `factory_contract.py --all` rechecks the current files.
Matching hashes show what an approval file pins; they cannot prove who
actually gave permission or verify a Sanskrit citation.

## Set up and inspect

Install the contract dependency in the production Python environment:

```sh
python3 -m pip install -r requirements-contract.txt
python3 factory_contract.py --all > /tmp/tantrasara-audit.json
python3 run_all.py --chapters 02 --dry-run
```

The existing renderer also needs its usual Pillow, `indic-transliteration`,
FFmpeg/FFprobe, MMS, Whisper, fonts, free Fish wrapper, human phoneme clips,
bell asset, mounted volume, and configured services. `--dry-run` does not
test all of those. `factory_contract.py --all --require-approval` exits 1
if *any* checked unit lacks a matching approval; that is expected while
there are blocked units.

For the regression suite, install `requirements-test.txt` and run
`python3 -m unittest discover -s tests -v`. GitHub Actions runs the same
suite and checks all source rebuilds; it deliberately does not call Fish,
Qwen, R2, or mark outstanding approvals as a CI failure.

`schemas/` defines the accepted storyboard, glossary, drop, historical
approval, render metadata, subtitles, proof, voice-energy, Qwen, assembly,
and ear-review shapes. `factory_contract.py` enforces the schemas plus
cross-file rules: unique ordered blocks, valid cue/drop references, green
storyboard, citation fields, exact approval hashes, and lane-specific paths.
Duplicate JSON keys, non-finite JSON numbers, unknown fields and missing
inputs fail. Proposed terms stay proposed. Confirmed literal display is
blocked until the conflicting V4/D3 rules are resolved by the owner.

Before a real audio or video build, the entry points check the owner-pinned
storyboard/glossary, source/override rebuild, planning gate, free Fish model
when Fish is called, and available storage. The storage check fails when
the volume cannot be verified. Production videos and mixes must be under
`~/vol/tantrasara/renders`. A real OS lock protects the shared video scratch
paths; a second per-output lock prevents two chunk planners touching the
same parts directory. `--from` is not permission to skip these checks.

## One chapter from audio to review

This is a working order, not permission to render an unapproved unit:

1. Publish a complete review pack and obtain the required render approval.
   Run the scoped rough probes and settle the suspects according to the
   existing owner rules. Generate only the required audio groups.
2. Run `run_all.py --chapters 02 --from video`, or run `run_blocks.py` on
   the storyboard and a parts directory **on the render volume**. It builds
   a group-aligned part, extracts its proof frames, runs the visual gate and
   stops with exit 2 / `PENDING_REVIEW`. It will not run the next part while
   this review is missing.
3. Inspect every PNG listed in `proofs/pNN/index.md` against the storyboard,
   captions and GATES. Complete `review.template.json` as `review.json`:
   identify the actual reviewer, date, and a specific observation and pass
   for every frame. A generated template is intentionally not a review.
   If anything is wrong, fix the cause, rebuild and review the new proof;
   an old review cannot bless changed frames or video. Rerun the command to
   continue to the next part.
4. After every part has been reviewed, `assemble_proven.py` rechecks the
   current inputs, proofs and reviews before concatenating. Its assembly
   receipt links the final bytes to the exact parts and review records.
   Chunks start only where a chant or tone break permits the previous hold
   to clear, so the nominal 600-second target can be exceeded. The bell is
   added only at the chapter opening; the normal boundary bed is retained.
5. `verify_clip.py` validates streams, levels, transcript coverage and
   motion, and writes a video- and storyboard-bound report and transcript.
   `check_voices.py` samples sound energy at each seat's onsets using only
   that video's subtitles. This can detect silent samples; it **cannot
   identify the speaker or prove pronunciation**.
6. `run_all.py` runs the Qwen final against the exact video, storyboard and
   transcript. It submits those materials to the configured Qwen endpoint.
   The report is bound to their hashes. Model `pass` is not a verdict:
   investigate each finding against the frames, transcript or measurements.
   Complete the Qwen disposition template only for claims shown to be
   unsupported; fix real defects and produce a new video and report.
7. The first golden check returns `PENDING_REVIEW`, not a fabricated pass.
   After the owner actually listens and approves the exact final bytes,
   record that decision as `review/chNN/ears.json` according to
   `schemas/ear-review.schema.json`, with an evidence reference. Never
   create this record from an agent's own listening or an earlier render.
   `golden.py seal NN VIDEO` requires reviewed parts, verification, the
   voice-energy report, Qwen disposition and this owner decision. Release
   requires the same evidence for **every requested chapter**.

The generated metadata binds a part to the storyboard, glossary, approval,
source, overrides, review-pack manifest, drops, builder code, named
art/fonts/bell and the actual audio bytes. An old part without this metadata
is unproven and is not reused. A `.publish-in-progress` marker blocks a
review pack after an interrupted publish until it is successfully republished.
The full assembly records the hashes of the part videos, proof manifests
and completed reviews. A file's existence or a green model opinion is not
a substitute for those checks.

## Queue and recovery

`python3 run_queue.py --refresh` derives a board and does not launch work.
The first refresh creates a local `REGISTRY.json` if needed. Use
`--run-next` explicitly to start the next eligible job. The queue refuses a
second launch while a job is recorded as running or the video lock is held.
After a stopped job has been examined and its review completed, refresh,
then use `--resume NN` and `--run-next`. A job without an explicit completion
marker stays unresolved; `watch.py` reports `UNKNOWN`, not success.
Registry and event files are runtime state, not a durable cross-machine
queue. A production scheduler still needs durable storage and reconciliation
across hosts before unattended fleet operation.

## Boundaries and remaining work

- The checks here were run on repository data and synthetic FFmpeg samples.
  This environment did **not** have the production volume, external fonts,
  human phoneme clips, MMS/Whisper models or service keys, so no real chapter
  was rendered, listened to, published or sealed in this change.
- Historical WAV names hash voice seat and directed text. Existing receipts do
  not consistently bind the actual Fish voice ID, model/wrapper version and
  human-source clip bytes. New video fingerprints catch a WAV changing but
  do not establish how a legacy WAV was generated. Audit or migrate those
  receipts before treating unattended reuse as proven.
- Video fingerprints do not capture every dependency, model weight, shared
  library or encoder behavior. Proof frames and listening remain necessary.
  The subtitle/Whisper check uses ordered matching, not a semantic guarantee
  that every word was correctly spoken.
- Legacy review packs were produced with truncated storyboard blocks and a
  timeline capped at 400 blocks. Republish them with the corrected scripts
  before relying on the fuller view; this change did not upload anything.
  A successful upload is recorded, but the publish step still needs a remote
  HEAD/byte check to independently prove the R2 objects match local files.
- `GATES.md` says a literal never appears on screen while another rule and
  the renderer allow a confirmed literal. White-coverage rules and historical
  owner notes also disagree. Do not silently choose an editorial policy;
  dispose these decisions and update law and code together.
- Candidate Devanāgarī is not source evidence. The earlier M23 citation
  concerns, provisional casting and the owner-controlled academic/visual
  decisions remain open. Schema validity is not philological verification.
- Old renders, proof records, verification reports and golden seals without
  the new fingerprints/receipts need fresh evidence. Do not relabel them as
  current or manufacture owner-ear records.
