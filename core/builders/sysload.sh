#!/usr/bin/env bash
# sysload: one-line capacity read before starting parallel work.
# Video builds stay exclusive regardless (lock); this gates PREP parallelism.
echo "cpus=$(nproc) $(free -g | awk '/^Mem:/{print "ram_free="$4"G"}') load=$(cut -d' ' -f1 /proc/loadavg)"
