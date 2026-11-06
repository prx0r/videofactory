#!/bin/bash
# Watchdog: keep the overnight render alive, independently of any agent
# session. Installed in cron (*/10). Does nothing while a supervisor or a
# build is running; relaunches the supervisor (own session) when the goal
# is unfinished and nothing is alive.
#
# "Unfinished" = /tmp/overnight.goal exists AND no *_full.mp4 newer than
# the goal file is being added. The supervisor removes the goal when done.
set -u
GOAL=/tmp/overnight.goal
LOG=/tmp/overnight_watchdog.log

[ -f "$GOAL" ] || exit 0

# a live supervisor or build means hands off
if pgrep -f "overnight(_v2)?\.sh" >/dev/null 2>&1 \
   || pgrep -f "core/builders/(batch|build_clip|run_blocks|render_chapter)[.]py" >/dev/null 2>&1; then
  exit 0
fi

echo "$(date -u +%FT%TZ) watchdog: nothing alive, goal unfinished — relaunching" >>"$LOG"
setsid nohup /home/ubuntu/videofactory/ops/overnight_v2.sh < /dev/null >/dev/null 2>&1 &
