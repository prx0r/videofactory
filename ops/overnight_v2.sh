#!/bin/bash
# Overnight render supervisor v2 (2026-11-06 owner order).
#
# Goal: wake up to every remaining unit rendered. Storyboard green + owner
# approval is the only gate; nothing downstream can stop a unit.
#
# Safety properties (why this cannot half-die):
#   * sequential — one video build at a time (video lock)
#   * skips any unit whose final already exists (restart-safe)
#   * one retry per unit, then moves on
#   * clears stale locks and frees part space between units
#   * volume guard before the shiva leg
#   * launched under setsid by ops/watchdog.sh (own session)
set -u
cd /home/ubuntu/videofactory

LOG=/tmp/overnight.log
GOAL=/tmp/overnight.goal
exec >>"$LOG" 2>&1
mkdir -p /home/ubuntu/vol/tantrasara/renders/finals /home/ubuntu/vol/shiva/renders/finals
touch "$GOAL"
echo "=========== overnight v2 start $(date -u +%FT%TZ) ==========="

drain() {
  local i=0
  while pgrep -f "core/builders/(batch|build_clip|run_blocks|render_chapter|prove_clip)[.]py" \
        >/dev/null 2>&1; do
    sleep 60; i=$((i+1))
    [ "$i" -gt 240 ] && { echo "drain timeout — continuing"; break; }
  done
  python3 - <<'PY'
import fcntl
try:
    f=open('/tmp/video_build.lock','a+')
    fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
    f.seek(0); f.truncate(); f.flush()
    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
except BlockingIOError:
    print('lock still held by a live build')
PY
}

vol_free_gb() { df -BG /home/ubuntu/vol 2>/dev/null | awk 'NR==2{gsub("G","",$4);print $4}'; }
local_free_gb() { df -BG /tmp 2>/dev/null | awk 'NR==2{gsub("G","",$4);print $4}'; }

cleanup_unit() {
  local stem="$1" blocks
  rm -rf /tmp/clip_frames /tmp/${stem}_proof_* 2>/dev/null
  for blocks in /home/ubuntu/vol/*/renders/${stem}_blocks; do
    [ -d "$blocks" ] && rm -rf "$blocks"
  done
}

final_for() { # $1 lane-dir (tantrasara|shiva) $2 stem
  echo "/home/ubuntu/vol/$1/renders/finals/${2}_full.mp4"
}

run_unit() { # $1 project lane $2 unit $3 stem $4 lane-dir
  local proj="$1" unit="$2" stem="$3" lane="$4" attempt fin
  fin=$(final_for "$lane" "$stem")
  if [ -s "$fin" ]; then echo "--- $proj/$unit already shipped, skip"; return 0; fi
  for attempt in 1 2; do
    echo "--- $(date -u +%FT%TZ) $proj/$unit attempt $attempt (vol $(vol_free_gb)G local $(local_free_gb)G)"
    python3 core/builders/batch.py --project "$proj" --units "$unit" --ship
    local rc=$?
    if [ -s "$fin" ]; then
      echo "--- $proj/$unit SHIPPED rc=$rc ($(du -h "$fin" | cut -f1))"
      cleanup_unit "$stem"
      return 0
    fi
    echo "--- $proj/$unit attempt $attempt rc=$rc, no final"
    drain
  done
  cleanup_unit "$stem"
  echo "--- $proj/$unit GAVE UP after 2 attempts"
  return 1
}

export VF_REPO=~/tantrasara VF_RENDERS=~/vol/tantrasara/renders \
       VF_R2=r2:svread-audio/tantrasara VF_SERIES=tantrasara
drain
for u in 14 15 16 17 18 19 20 21 22; do
  run_unit tantrasara "$u" "ch$u" tantrasara
  drain
done

export VF_RENDERS=~/vol/shiva/renders VF_R2=r2:svread-audio/shiva VF_SERIES=shiva-sutras
for i in $(seq 0 77); do
  u=$(printf 's%02d' "$i")
  if [ "$(vol_free_gb)" -lt 3 ] 2>/dev/null; then
    echo "--- volume low ($(vol_free_gb)G) — stopping shiva leg"; break
  fi
  run_unit shiva-sutras "$u" "$u" shiva
  drain
done

rm -f "$GOAL"
echo "=========== overnight v2 done $(date -u +%FT%TZ) ==========="
echo "tantrasara finals: $(ls /home/ubuntu/vol/tantrasara/renders/finals/*_full.mp4 2>/dev/null | wc -l)"
echo "shiva finals: $(ls /home/ubuntu/vol/shiva/renders/finals/*_full.mp4 2>/dev/null | wc -l)"
