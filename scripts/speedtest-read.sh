#!/bin/bash
# speedtest-read.sh — Serve the cached speedtest JSON and trigger a
# background refresh ONLY when the cache is older than SPEEDTEST_REFRESH.
#
# Decouples Zabbix polling from speedtest cadence: the master item can poll
# every 2 min for fast first-collection / responsive dashboards, while the
# actual speedtest only runs every SPEEDTEST_REFRESH seconds (default 30 min).
# flock still prevents overlapping runs even if two pollers race past the
# staleness check.
#
# Env overrides: SPEEDTEST_CACHE, SPEEDTEST_LOCK, SPEEDTEST_SCRIPT,
# SPEEDTEST_REFRESH.

set -u

CACHE="${SPEEDTEST_CACHE:-/var/tmp/zabbix-speedtest.json}"
LOCK="${SPEEDTEST_LOCK:-/var/tmp/zabbix-speedtest.lock}"
SCRIPT="${SPEEDTEST_SCRIPT:-/etc/zabbix/scripts/speedtest-stats.sh}"
REFRESH="${SPEEDTEST_REFRESH:-1800}"

cat "$CACHE" 2>/dev/null || printf '{"error":"no cached speedtest result yet"}\n'

# Skip the bg refresh if the cache is fresh enough.
if [ -e "$CACHE" ]; then
  now=$(date +%s)
  mtime=$(stat -c %Y "$CACHE" 2>/dev/null || echo 0)
  [ $((now - mtime)) -lt "$REFRESH" ] && exit 0
fi

# First-create the lock world-writable so both the zabbix agent user and a
# human invoking zabbix_agent2 -t can flock it. Idempotent and silent.
[ -e "$LOCK" ] || ( umask 0111; : > "$LOCK" ) 2>/dev/null || true

# Fire-and-forget refresh under flock. Stderr silenced inside the subshell
# before opening FD 9 so a permission-denied cannot leak. If we cannot
# open the lock or another run holds it, exit 0 — refresh skipped silently.
(
  exec 2>/dev/null
  exec 9>"$LOCK" || exit 0
  flock -n 9 || exit 0
  "$SCRIPT"
) </dev/null >/dev/null 2>&1 &
disown 2>/dev/null || true
