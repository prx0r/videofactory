#!/bin/bash
# Overnight render supervisor (2026-11-06 owner order).
#
# Renders every remaining unit one at a time (one video build at a time),
# retries each unit once, cleans transient/part space between units, and
# keeps going no matter what a single unit does. Storyboard green + owner
# approval is the only gate; nothing downstream can stop a unit.
set -u
cd /home/ubuntu/videofactory

LOG=/tmp/overnight.log
exec >>"$LOG" 2>&1
echo "=========== overnight start $(date -u +%FT%TZ) ==========="

# Wait for any in-flight build/test to finish (never two video builds).
drain() {
  local i=0
  while pgrep -f "core/builders/(batch|build_clip|run_blocks|render_chapter|prove_clip)[.]py" \
        >/dev/null 2>&1 || pgrep -f "test_oom" >/dev/null 2>&1; do
    sleep 60
    i=$((i+1))
    [ "$i" -gt 240 ] && { echo "drain timeout — clearing stale lock"; break; }
  done
  # a PID-text-only lock is stale; real flock is released with the process
  python3 - <<'PY'
import fcntl, os
p='/tmp/video_build.lock'
try:
    f=open(p,'a+')
    fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
    f.seek(0); f.truncate(); f.flush()
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
except BlockingIOError:
    print('lock still held by a live build')
PY
}

vol_free_gb() { df -BG /home/ubuntu/vol 2>/dev/null | awk 'NR==2{gsub("G","",$4);print $4}'; }
local_free_gb() { df -BG /tmp 2>/dev/null | awk 'NR==2{gsub("G","",$4);print $4}'; }

cleanup_unit() { # $1 = lane dir prefix (tantrasara|shiva)
  local stem="$1"
  # frames + proof scratch are transient
  rm -rf /tmp/clip_frames /tmp/${stem}_proof_* 2>/dev/null
  # the per-unit block dir is rebuildable from cached audio: free the volume
  local blocks
  for blocks in /home/ubuntu/vol/*/renders/${stem}_blocks; do
    [ -d "$blocks" ] && rm -rf "$blocks"
  done
}

run_unit() { # $1 project lane, $2 unit id, $3 stem
  local proj="$1" unit="$2" stem="$3"
  local attempt
  for attempt in 1 2; do
    echo "--- $(date -u +%FT%TZ) $proj/$unit attempt $attempt (vol $(vol_free_gb)G local $(local_free_gb)G)"
    python3 core/builders/batch.py --project "$proj" --units "$unit" --ship
    local rc=$?
    if [ -f "/home/ubuntu/vol/${proj_dir}/renders/finals/${stem}_full.mp4" ]; then
      echo "--- $proj/$unit SHIPPED (rc=$rc)"
      cleanup_unit "$stem"
      return 0
    fi
    echo "--- $proj/$unit attempt $attempt rc=$rc, no final yet"
    attempt=$((attempt+1))
  done
  cleanup_unit "$stem"
  echo "--- $proj/$unit GAVE UP after 2 attempts"
  return 1
}

# Tantrasara 14-22 (the nine that have never shipped)
export VF_REPO=~/tantrasara VF_RENDERS=~/vol/tantrasara/renders \
       VF_R2=r2:svread-audio/tantrasara VF_SERIES=tantrasara
proj_dir="tantrasara"
drain
for u in 14 15 16 17 18 19 20 21 22; do
  run_unit tantrasara "$u" "ch$u"
  drain
done

# Shiva s00-s77 (owner blanket bless). Needs audio on the way; keep going
# while the volume has room.
export VF_RENDERS=~/vol/shiva/renders VF_R2=r2:svread-audio/shiva VF_SERIES=shiva-sutras
proj_dir="shiva"
for i in $(seq 0 77); do
  u=$(printf 's%02d' "$i")
  if [ "$(vol_free_gb)" -lt 3 ] 2>/dev/null; then
    echo "--- volume low ($(vol_free_gb)G) — stopping shiva leg"
    break
  fi
  run_unit shiva-sutras "$u" "$u"
  drain
done

echo "=========== overnight done $(date -u +%FT%TZ) ==========="
echo "FINALS:"; ls -la /home/ubuntu/vol/tantrasara/renders/finals/*_full.mp4 /home/ubuntu/vol/shiva/renders/finals/*_full.mp4 2>/dev/null | wc -l
