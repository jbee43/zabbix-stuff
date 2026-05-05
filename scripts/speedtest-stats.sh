#!/bin/bash
# speedtest-stats.sh — Run LibreSpeed CLI and write atomic JSON to a cache file.
#
# Intended to be invoked by cron / systemd timer, NOT directly by the Zabbix
# agent (a full speedtest takes 30-60 s, which exceeds the agent's hard
# Timeout limit of 30 s). The Zabbix UserParameter reads the cached file.
#
# Requires: librespeed-cli, jq, bash.

set -euo pipefail

CACHE_FILE="${SPEEDTEST_CACHE:-/var/tmp/zabbix-speedtest.json}"
TMP_FILE="${CACHE_FILE}.tmp.$$"
CLI="${LIBRESPEED_CLI:-librespeed-cli}"

trap 'rm -f "$TMP_FILE"' EXIT

emit() {
  # Atomic write: same filesystem rename, never seen half-written by readers.
  printf '%s\n' "$1" > "$TMP_FILE" && mv -f "$TMP_FILE" "$CACHE_FILE"
}

emit_error() {
  emit "{\"error\":\"$1\",\"collected_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"collected_at_ts\":$(date -u +%s)}"
  exit 0
}

command -v "$CLI" >/dev/null 2>&1 || emit_error "librespeed-cli not found"
command -v jq    >/dev/null 2>&1 || emit_error "jq not found"

RAW=$(timeout 120 "$CLI" --json --secure --no-icmp --telemetry-level=disabled 2>/dev/null) \
  || emit_error "librespeed-cli execution failed or timed out"

[ -n "$RAW" ] || emit_error "librespeed-cli returned empty output"

JSON=$(printf '%s' "$RAW" | jq -c '.[0] | {
    download_bps:    ((.download // 0) * 1000000 | floor),
    upload_bps:      ((.upload   // 0) * 1000000 | floor),
    ping_ms:         (.ping   // 0),
    jitter_ms:       (.jitter // 0),
    server_name:     (.server.name // "Unknown"),
    server_host:     (.server.url  // ""),
    isp:             (.client.isp  // "Unknown"),
    result_url:      (.share // ""),
    collected_at:    (now | strftime("%Y-%m-%dT%H:%M:%SZ")),
    collected_at_ts: (now | floor)
  }' 2>/dev/null) \
  || emit_error "failed to parse librespeed-cli JSON"

emit "$JSON"
