# Speedtest / Internet (LibreSpeed)

**Template:** `templates/speedtest.json`
**Script:** `scripts/speedtest-stats.sh`
**Config:** `userparameters/speedtest.conf`
**Name:** Speedtest by Zabbix agent active
**Group:** Templates

Internet performance monitoring via the [LibreSpeed CLI](https://github.com/librespeed/speedtest-cli) — open source, no telemetry, no license prompts. Measures download/upload speed, latency, and jitter.

A full speedtest takes 30-60 s, which exceeds the Zabbix agent's hard `Timeout` ceiling (max 30 s). To work around that, **polling and the actual speedtest are decoupled**:

- The Zabbix agent polls the master item every 2 min (configurable). Each poll just `cat`s a JSON cache — sub-millisecond, dashboards stay responsive, first-collection after import is fast.
- The read wrapper checks the cache's mtime; if it's older than `SPEEDTEST_REFRESH` (default 30 min), it kicks off a real speedtest in the background under `flock`. Otherwise it just exits — no link saturation from frequent polls.

Pieces:

- `speedtest-stats.sh` — runs LibreSpeed CLI, writes the result atomically (`tmp` + `mv`) to `/var/tmp/zabbix-speedtest.json`. Slow path, ~60 s.
- `speedtest-read.sh` — `cat`s the cache (sub-ms), and only when the cache is stale (`mtime > SPEEDTEST_REFRESH`) fires `speedtest-stats.sh` in the background under flock. Fast path, called by the agent.

For a script-free, host-free alternative running entirely from the Zabbix server, see [`speedtest-cloudflare.md`](speedtest-cloudflare.md).

## Methodology and accuracy

LibreSpeed runs **on the monitored host** and uses **multiple parallel HTTPS streams**, so it gets close to nominal line speed. Expect LibreSpeed to report roughly **70-80% of the line's marketed speed** on a healthy connection (e.g. ~750 Mbps on a 1 Gbps line) — the 20-30% gap comes from TCP/TLS overhead, ISP peering quality, and (on a Pi) single-core CPU bound on TLS at gigabit.

This is the more accurate of the two speedtest templates in this repo. Use it when you need the real number; use [`speedtest-cloudflare.md`](speedtest-cloudflare.md) only when you can't (or don't want to) install anything on the host.

## Prerequisites

LibreSpeed CLI is a single static Go binary — no apt repo, no license dance.

```bash
# Auto-detects arch: x86_64 → linux_amd64, aarch64 (Pi 5 / Pi 4 64-bit) → linux_arm64,
# armv7l (32-bit Pi OS) → linux_armv7. armv6l (Pi Zero / Pi 1) is not published.
VER=1.0.11
case "$(uname -m)" in
  x86_64)  ARCH=linux_amd64 ;;
  aarch64) ARCH=linux_arm64 ;;
  armv7l)  ARCH=linux_armv7 ;;
  *) echo "Unsupported arch: $(uname -m)"; exit 1 ;;
esac
curl -fsSL "https://github.com/librespeed/speedtest-cli/releases/download/v${VER}/librespeed-cli_${VER}_${ARCH}.tar.gz" \
  | sudo tar -xz -C /usr/local/bin librespeed-cli
sudo chmod +x /usr/local/bin/librespeed-cli
sudo apt install -y jq

# Verify
librespeed-cli --version
```

## Setup

Deploy both scripts and the UserParameter:

```bash
sudo cp scripts/speedtest-stats.sh scripts/speedtest-read.sh /etc/zabbix/scripts/
sudo chmod +x /etc/zabbix/scripts/speedtest-stats.sh /etc/zabbix/scripts/speedtest-read.sh
sudo cp userparameters/speedtest.conf /etc/zabbix/zabbix_agent2.d/
sudo systemctl restart zabbix-agent2
```

Prime the cache once so the very first agent poll has data (otherwise the item reports `{"error":"no cached speedtest result yet"}` until the first background refresh completes — about 60 s after the first poll):

```bash
sudo -u zabbix /etc/zabbix/scripts/speedtest-stats.sh
cat /var/tmp/zabbix-speedtest.json
```

Cache and lock paths can be overridden via the `SPEEDTEST_CACHE` and `SPEEDTEST_LOCK` env vars (set them in the UserParameter line if you do). The actual speedtest cadence is controlled by `SPEEDTEST_REFRESH` in seconds (default 1800 = 30 min). To run a speedtest every 15 min instead:

```text
UserParameter=speedtest.stats,SPEEDTEST_REFRESH=900 /etc/zabbix/scripts/speedtest-read.sh
```

## Items

| Item | Units | Description |
|---|---|---|
| Download speed | bps | Download bandwidth |
| Upload speed | bps | Upload bandwidth |
| Ping latency | ms | Server round-trip time |
| Jitter | ms | Latency variation |
| Server name | text | LibreSpeed server used |
| ISP | text | Detected ISP (from client IP) |
| Result URL | text | Share URL (only if LibreSpeed server has telemetry enabled) |

No LLD — single result per run. **Packet loss is not measured by LibreSpeed.**

## Triggers

| Trigger | Severity | Default |
|---|---|---|
| Download < DISASTER | DISASTER | 500 Mbps |
| Download < WARNING | WARNING | 800 Mbps |
| Upload < WARNING | WARNING | 400 Mbps |
| Ping > HIGH | HIGH | 50 ms |
| Ping > WARNING | WARNING | 20 ms |
| No data received | WARNING | 90m |

Download WARNING depends on DISASTER. Ping WARNING depends on HIGH.

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$SPEEDTEST.DL.WARNING}` | 600000000 | Download warning threshold (bps, 600 Mbps — sized for healthy 1 Gbps as measured by LibreSpeed) |
| `{$SPEEDTEST.DL.DISASTER}` | 300000000 | Download disaster threshold (bps, 300 Mbps — degraded health, not nominal) |
| `{$SPEEDTEST.UL.WARNING}` | 300000000 | Upload warning threshold (bps, 300 Mbps — sized for symmetric gigabit) |
| `{$SPEEDTEST.PING.WARNING}` | 20 | Ping warning (ms) |
| `{$SPEEDTEST.PING.HIGH}` | 50 | Ping high (ms) |
| `{$SPEEDTEST.NODATA}` | 90m | No-data timeout |

Override macros per host to match your ISP plan.

## Dashboard

Single-page "Overview":

- Top row: Download speed + Upload speed (side by side)
- Bottom row: Ping + Jitter (full width, overlay)

## Data Retention

| Category | History | Trends |
|---|---|---|
| Download, upload, ping, jitter | 14d | 365d |
| Server, ISP | 7d | — |
| Result URL | 7d | — |
| Master item (JSON) | — | — |

## Sources

- [LibreSpeed CLI](https://github.com/librespeed/speedtest-cli)
- [LibreSpeed project](https://librespeed.org/)
