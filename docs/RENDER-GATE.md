# RENDER GATE — storyboard only (owner order 2026-11-06)

> "There should be no gate for render after it passes storyboard. That's
> it. It's only render then. I don't want any fails holding things up."

## The one gate

`factory_contract.validate_storyboard_gate(storyboard)`:

1. storyboard schema valid, block ids contiguous, validation 0e 0w
2. owner approval (`approved_chNN.json`) hashes match these exact bytes

That is the whole gate. If it passes, the unit renders to completion.

## Everything else is advisory / record-only

| check | was | now |
|---|---|---|
| audio-complete | blocking | prints, records, continues |
| list-geometry | blocking | prints, records, continues |
| hold-scan (60s) | advisory already | advisory |
| review pack current | blocking | advisory |
| source/override rebuild | blocking | advisory |
| free-tier pin | blocking | advisory (still printed loudly) |
| prove (H3/H6/drops) | blocking | record-only beside each part |
| issues (check_issues) | could hold launch | work list only |
| ship (R2) | blocking on byte-match | still blocking (real delivery failure) |

Real breakage still stops a unit: a render crash, a failed concat, or an
R2 byte-mismatch. Nothing else.

## Why this is safe

The renderer is now self-consistent with the gates that remain:

* **one cue per block** (renderer + H3 + H8 + list-geometry + scans),
  so same-block stack runs cannot form (the ch16 crash class is gone);
* **alignment is OOM-proof**: 3 transient retries, then adaptive
  recursive splitting until pieces fit (a 278-word group drove the MMS
  aligner to 7.6GB and was kernel-killed; 611 words now align at
  mean 0.909);
* **H-list runs the renderer-identical run check**, not the old
  worst-case-5 model that false-failed ch20;
* **H7 reads the unit's own lane drops file** (never another chapter's).

Defects are still visible: issue files, prove sidecars, verify reports,
ship verdicts and the batch log all record what failed. The owner reads
them; they do not stop the line.

## Overnight operation

`ops/overnight.sh` (detached): drains any in-flight build, then renders
each remaining unit sequentially with one retry, clearing stale locks and
freeing part space between units. Volume-guarded before the shiva leg.
Log: `/tmp/overnight.log`.
