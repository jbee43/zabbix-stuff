# Speedtest / Internet (Cloudflare, HTTP-only)

**Template:** `templates/speedtest-cloudflare.json`
**Script:** none
**Config:** none
**Name:** Speedtest Cloudflare by HTTP
**Group:** Templates

Script-free internet performance monitoring against Cloudflare's edge (`speed.cloudflare.com`). Uses Zabbix native HTTP agent + JavaScript preprocessing — **nothing is deployed to the monitored host**. The Zabbix server (or proxy) runs the test itself, so this template is ideal for monitoring the egress of any host that has the agent installed (or even a virtual host that has none).

For a host-side speedtest with conventional CLI, see [`speedtest.md`](speedtest.md).

## Methodology and accuracy

This template **systematically under-measures fast lines.** On a 1 Gbps line, expect this template to report ~30-50% of nominal speed (i.e. 300-500 Mbps), not because the link is slow but because of how the test works:

- **Single TCP/TLS stream** (real speed tests use 4-8 parallel streams to saturate)
- **Small payload** (5 MB default, vs. 25-100 MB for Ookla / LibreSpeed) — TCP slow-start barely opens before the transfer ends
- **Runs from the Zabbix server / proxy**, not from the monitored host — so the result reflects the Zabbix host's path to Cloudflare, not the host you linked the template to
- **JS preprocessing in Duktape** adds per-byte overhead receiving the response into a string

That's why the macro defaults below are calibrated to **what this template actually reports**, not to nominal line speed. They target "is the link broadly healthy?" rather than "am I getting my full plan?".

If you have gigabit and want accurate numbers, prefer [`speedtest.md`](speedtest.md) (LibreSpeed) — it runs parallel streams from the host itself and reports ~70-80% of nominal even on a healthy link. Use this Cloudflare template when you can't install a CLI on the host, or as a complementary "agentless edge probe" alongside LibreSpeed.

You can bump `{$SPEEDTEST.CF.DL_BYTES}` (e.g. to 50 MB) to narrow the gap somewhat, but the single-stream + Zabbix-server-side limitations remain — it will never quite match a real multi-stream test.

## Methodology

The master item fetches the tiny `https://speed.cloudflare.com/cdn-cgi/trace` endpoint (PoP / country metadata). JavaScript preprocessing then runs:

1. **Latency** — `{$SPEEDTEST.CF.PING_SAMPLES}` 1-byte fetches to `__down?bytes=1`, averaged. Jitter is the mean absolute deviation between consecutive samples.
2. **Download** — single timed `GET https://speed.cloudflare.com/__down?bytes=N` of `{$SPEEDTEST.CF.DL_BYTES}` bytes. `bps = body_length * 8 / elapsed`.
3. **Upload** — single timed `POST https://speed.cloudflare.com/__up` of `{$SPEEDTEST.CF.UL_BYTES}` bytes.

### Honest limitations

- **Single-stream HTTPS.** Comparable to Ookla / LibreSpeed only at the order-of-magnitude level. May underreport on high-BDP links (>500 Mbps with high latency) where multi-stream tools win.
- **You measure to the closest Cloudflare PoP**, not to "the internet" in general. For ISP plan validation that is usually exactly what you want.
- **No packet loss.** HTTP cannot expose it cleanly.
- **Constrained by Zabbix server's JS preprocessing time budget.** Defaults (5 MB DL / 2 MB UL / 5 ping samples) are tuned to fit comfortably in 10 s. Bump payloads only if your `zabbix_server.conf` `Timeout` is also increased.

## Setup

Nothing to install — just import and link the template:

1. **Data collection → Templates → Import** → `templates/speedtest-cloudflare.json`
2. Link to any host (the host doesn't need an agent; the test runs from the Zabbix server / proxy)
3. Override macros per host if your ISP plan differs from the defaults

The Zabbix server / proxy must be able to reach `speed.cloudflare.com` over HTTPS.

## Items

| Item | Units | Description |
|---|---|---|
| Download speed | bps | Single-stream HTTPS GET throughput |
| Upload speed | bps | Single-stream HTTPS POST throughput |
| Ping latency | ms | Average HTTP round-trip to Cloudflare PoP |
| Jitter | ms | Mean absolute deviation between ping samples |
| Cloudflare PoP | text | IATA-style code (e.g. `LIS`, `MAD`, `FRA`) |
| Country | text | ISO country code as seen by Cloudflare |

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
| `{$SPEEDTEST.CF.DL.WARNING}` | 250000000 | Download warning threshold (bps, 250 Mbps — calibrated to **what this template reports**, not raw line speed) |
| `{$SPEEDTEST.CF.DL.DISASTER}` | 100000000 | Download disaster threshold (bps, 100 Mbps — calibrated to template methodology) |
| `{$SPEEDTEST.CF.DL_BYTES}` | 5000000 | Download payload size (5 MB default) |
| `{$SPEEDTEST.CF.NODATA}` | 90m | No-data timeout |
| `{$SPEEDTEST.CF.PING.HIGH}` | 50 | Ping high (ms) |
| `{$SPEEDTEST.CF.PING.WARNING}` | 20 | Ping warning (ms) |
| `{$SPEEDTEST.CF.PING_SAMPLES}` | 5 | Latency probe count |
| `{$SPEEDTEST.CF.UL.WARNING}` | 100000000 | Upload warning threshold (bps, 100 Mbps — calibrated to template methodology) |
| `{$SPEEDTEST.CF.UL_BYTES}` | 2000000 | Upload payload size (2 MB default) |

## Dashboard

Single-page "Overview":

- Top row: Download speed + Upload speed (side by side, Cloudflare orange / green)
- Bottom row: Ping + Jitter (full width, overlay)

## Data Retention

| Category | History | Trends |
|---|---|---|
| Download, upload, ping, jitter | 14d | 365d |
| PoP, country | 7d | — |
| Master item (JSON) | — | — |

## Sources

- [Cloudflare speed test](https://speed.cloudflare.com/)
- [Cloudflare cdn-cgi/trace](https://developers.cloudflare.com/fundamentals/reference/cdn-cgi-endpoint/)
