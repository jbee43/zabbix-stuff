# AdGuard Home

**Template:** `templates/adguard-home.json`
**Name:** AdGuard Home by HTTP
**Group:** Templates

AdGuard Home DNS ad-blocker monitoring via REST API. Tracks DNS query statistics, blocking rates, processing time, and service status.

No agent required — uses HTTP agent items with Basic Auth.

## Prerequisites

- AdGuard Home instance with web interface accessible from the Zabbix server/proxy
- API credentials (username/password for Basic Auth)

## Setup

1. Import `templates/adguard-home.json` in Zabbix UI
2. Assign template to a host
3. Set required macros on the host:
   - `{$ADGUARD.HOST}` — AdGuard Home hostname or IP
   - `{$ADGUARD.PORT}` — Web interface port (default: 3000)
   - `{$ADGUARD.USER}` — API username
   - `{$ADGUARD.PASSWORD}` — API password (stored as secret)

## Items

### Statistics (from `/control/stats`)

| Item | Units | Description |
|---|---|---|
| DNS queries | count | Total DNS queries in the stats period |
| Blocked by filters | count | Queries blocked by filter rules |
| Blocked by safebrowsing | count | Queries blocked by safebrowsing |
| Blocked by parental | count | Queries blocked by parental control |
| Avg processing time | s | Average DNS query processing time |
| Block percentage | % | Calculated: blocked / total queries |

### Status (from `/control/status`)

| Item | Description |
|---|---|
| Protection enabled | DNS filtering protection state (Enabled/Disabled) |
| Running | AdGuard Home service state (Running/Stopped) |
| Version | Current AdGuard Home version |
| DNS port | Configured DNS listening port |

## Triggers

| Trigger | Severity | Default |
|---|---|---|
| Service not running | DISASTER | — |
| Protection disabled | HIGH | — |
| Avg processing time > HIGH | HIGH | 0.5s |
| Avg processing time > WARNING | WARNING | 0.1s |
| Version changed | INFO | — |
| No data received | WARNING | 15m |

Processing time triggers use dependency chains.

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$ADGUARD.HOST}` | localhost | AdGuard Home hostname or IP |
| `{$ADGUARD.PORT}` | 3000 | Web interface port |
| `{$ADGUARD.USER}` | (empty) | HTTP Basic Auth username |
| `{$ADGUARD.PASSWORD}` | (empty) | HTTP Basic Auth password (secret) |
| `{$ADGUARD.PROC.WARNING}` | 0.1 | Avg processing time warning (seconds) |
| `{$ADGUARD.PROC.HIGH}` | 0.5 | Avg processing time high (seconds) |
| `{$ADGUARD.NODATA}` | 15m | No-data timeout |

## Dashboard

Single-page "Overview" dashboard:

- Top row: DNS queries graph + Block percentage graph
- Middle row: Avg processing time graph
- Bottom row: Protection status, Running status, Version widgets

## Data Retention

| Category | History | Trends |
|---|---|---|
| Queries, blocking, processing time | 14d | 365d |
| Protection/running status | 14d | — |
| Version, DNS port | 1d | — |
| Master items (JSON) | — | — |

## Sources

- [AdGuard Home API](https://github.com/AdguardTeam/AdGuardHome/wiki/Configuration#api)
