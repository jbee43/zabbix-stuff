# zabbix-stuff

## TLDR

Zabbix templates and scripts

## Templates

| Template               | File                        | Docs                                 | Targets                | Collection |
| ---------------------- | --------------------------- | ------------------------------------ | ---------------------- | ---------- |
| AdGuard Home           | `adguard-home.json`         | [docs](docs/adguard-home.md)         | AdGuard Home           | HTTP agent |
| EVE Online             | `eve-online.json`           | [docs](docs/eve-online.md)           | ESI API                | HTTP agent |
| Linux HW (lm-sensors)  | `linux-hw-lm-sensors.json`  | [docs](docs/linux-hw-lm-sensors.md)  | Ubuntu/Debian x86_64   | Agent 2    |
| Raspberry Pi           | `raspberry-pi.json`         | [docs](docs/raspberry-pi.md)         | Pi 2/3/4/5, Zero 2 W   | Agent 2    |
| Speedtest (Cloudflare) | `speedtest-cloudflare.json` | [docs](docs/speedtest-cloudflare.md) | Internet (server-side) | HTTP agent |
| Speedtest (LibreSpeed) | `speedtest.json`            | [docs](docs/speedtest.md)            | Linux                  | Agent 2    |
| Weather (IPMA)         | `ipma-weather.json`         | [docs](docs/ipma-weather.md)         | IPMA API               | HTTP agent |

## How to Use

### Import Template

1. In Zabbix UI: **Data collection → Templates → Import**
2. Select the `.json` file from `templates/`
3. Import (update existing if reimporting)

### Agent-Based Templates Setup

Templates using Zabbix Agent 2 (`linux-hw-lm-sensors`, `raspberry-pi`, `speedtest`) require deploying a script and UserParameter config:

```bash
# Copy script(s)
sudo cp scripts/<script> /etc/zabbix/scripts/
sudo chmod +x /etc/zabbix/scripts/<script>

# Copy UserParameter config
sudo cp userparameters/<template>.conf /etc/zabbix/zabbix_agent2.d/

# Restart agent
sudo systemctl restart zabbix-agent2
```

Per-template script files:

- `linux-hw-lm-sensors` → `scripts/lm-sensors-stats.py`
- `raspberry-pi` → `scripts/rpi-hw-stats.sh`
- `speedtest` → `scripts/speedtest-stats.sh` + `scripts/speedtest-read.sh` (the latter is a fast-path wrapper that returns the cached JSON and triggers a background refresh only when the cache is stale)

### HTTP Agent Templates

`adguard-home`, `eve-online`, `ipma-weather`, and `speedtest-cloudflare` use the Zabbix HTTP agent and need no host-side deployment, they poll APIs directly from the Zabbix server or proxy

Just import, assign to a host, and configure the endpoint macros

## Template Highlights

- **[Raspberry Pi](docs/raspberry-pi.md)** - All Pi models: thermal zones, voltages, 8-bit throttle status, CPU/GPU frequency, fan state, NVMe temperatures, Pi 5 PMIC power readings
- **[Linux HW (lm-sensors)](docs/linux-hw-lm-sensors.md)** - Auto-discovers all sensors on x86_64 Ubuntu/Debian: temperatures, fans, voltages, power via `sensors -j`
- **[AdGuard Home](docs/adguard-home.md)** - DNS query stats, blocking rate, processing time, protection/service status via REST API
- **[Speedtest (LibreSpeed)](docs/speedtest.md)** - Download/upload speed, ping, jitter via LibreSpeed CLI on the host
- **[Speedtest (Cloudflare)](docs/speedtest-cloudflare.md)** - Same metrics, but script-free: native HTTP agent + JS preprocessing, runs from the Zabbix server
- **[Weather (IPMA)](docs/ipma-weather.md)** - Portugal: today snapshot tiles + 5-day daily-forecast graphs + per-category warnings (awareness 0–3 + validity window) + max-awareness/active-count summaries
- **[EVE Online](docs/eve-online.md)** - PLEX price, player count, server status, ...

## CI/CD (GitHub Actions)

Workflows under `.github/workflows/`:

- **ci.yml** - JSON validation, template structure lint via `scripts/ci/lint-templates.py`, shellcheck, ruff, yamllint, markdownlint, docs completeness
- **security.yml** - Gitleaks (PR-range on PRs, full-history otherwise) and credential lint via `lint-templates.py` (enforces SECRET_TEXT for password/secret/token/apikey macros)

## Compatibility

- **Zabbix version:** 7.2+ (template export format 7.2)
- **Agent:** Zabbix Agent 2 (active checks)
- **Platforms:** Linux (bash + Python collection scripts)

## References

- [Zabbix template guidelines](https://www.zabbix.com/documentation/7.2/en/manual/config/templates)
- [Raspberry Pi vcgencmd](https://www.raspberrypi.com/documentation/computers/os.html#vcgencmd)
- [Raspberry Pi get_throttled](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled)
- [lm-sensors](https://github.com/lm-sensors/lm-sensors)
- [AdGuard Home API](https://github.com/AdguardTeam/AdGuardHome/wiki/Configuration#api)
- [LibreSpeed CLI](https://github.com/librespeed/speedtest-cli)
- [Cloudflare speed test](https://speed.cloudflare.com/)
- [IPMA Open Data](https://api.ipma.pt/)

> **Read-only mirror**: this repository is automatically synced from a private Gitea instance
