# Raspberry Pi

**Template:** `templates/raspberry-pi.json`
**Script:** `scripts/rpi-hw-stats.sh`
**Config:** `userparameters/raspberry-pi.conf`
**Name:** Raspberry Pi by Zabbix agent active
**Group:** Templates/Server hardware

Comprehensive hardware monitoring for all Raspberry Pi models. Single master item collects everything as JSON every 2 minutes; dependent items and LLD extract individual metrics.

## Prerequisites

```bash
# On Ubuntu (Pi 5)
sudo apt install libraspberrypi-bin

# On Raspberry Pi OS — vcgencmd is pre-installed

# Allow zabbix user to access vcgencmd
sudo usermod -aG video zabbix
```

## Setup

```bash
sudo cp scripts/rpi-hw-stats.sh /etc/zabbix/scripts/
sudo chmod +x /etc/zabbix/scripts/rpi-hw-stats.sh
sudo cp userparameters/raspberry-pi.conf /etc/zabbix/zabbix_agent2.d/
sudo systemctl restart zabbix-agent2
```

## Discovered Items (LLD)

| Discovery | Macros | Items per instance |
|---|---|---|
| Thermal zones | `{#ZONE}`, `{#ZONE.TYPE}` | Temperature (°C) |
| NVMe devices | `{#NVME.DEVICE}` | NVMe temperature (°C) |
| Voltage rails | `{#VOLTAGE.TYPE}` | Voltage (V) |

**Thermal zones by model:**

- Pi 2/3/4: `cpu-thermal`
- Pi 5: `cpu-thermal`, `gpu-thermal`, `rp1_adc-thermal`

## Static Items

| Item | Description |
|---|---|
| Model | Pi model string |
| CPU frequency | Current ARM clock (MHz) |
| CPU max frequency | Max configured ARM clock (MHz) |
| GPU frequency | VideoCore clock (MHz) |
| Fan state | PWM state: Off/Low/Medium/High/Full/N/A |
| Fan speed | Active cooler tach RPM (Pi 5; 0 if no tach fan) |
| Power consumption | Total system watts from PMIC rail V x A (Pi 5; 0 on older Pis) |
| Throttle: under-voltage detected | Bit 0 — power supply issue (current) |
| Throttle: ARM frequency capped | Bit 1 — frequency limited (current) |
| Throttle: currently throttled | Bit 2 — active throttling (current) |
| Throttle: soft temp limit active | Bit 3 — thermal limit (current) |
| Throttle: under-voltage occurred | Bit 16 — since boot (sticky) |
| Throttle: freq capping occurred | Bit 17 — since boot (sticky) |
| Throttle: throttling occurred | Bit 18 — since boot (sticky) |
| Throttle: soft temp limit occurred | Bit 19 — since boot (sticky) |
| Throttle: human-readable summary | Decoded text — `OK` or `NOW: ... \| SINCE BOOT: ...` |

## Triggers

| Trigger | Severity | Default |
|---|---|---|
| Temperature > WARNING | WARNING | 70°C |
| Temperature > AVERAGE | AVERAGE | 75°C |
| Temperature > HIGH | HIGH | 80°C |
| Temperature > DISASTER | DISASTER | 85°C |
| NVMe temp > WARNING | WARNING | 60°C |
| NVMe temp > HIGH | HIGH | 70°C |
| NVMe temp > DISASTER | DISASTER | 80°C |
| Under-voltage detected | HIGH | — |
| ARM frequency capped | WARNING | — |
| Currently throttled | AVERAGE | — |
| Soft temp limit active | WARNING | — |
| Under-voltage occurred since boot | WARNING | — |
| No data received | WARNING | 10m |

All temperature triggers use 5-minute average. Trigger dependencies prevent alert storms (DISASTER suppresses HIGH suppresses AVERAGE suppresses WARNING).

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$RPI.TEMP.WARNING}` | 70 | SoC warning threshold (°C) |
| `{$RPI.TEMP.AVERAGE}` | 75 | SoC average threshold (°C) |
| `{$RPI.TEMP.HIGH}` | 80 | SoC high threshold (°C) |
| `{$RPI.TEMP.DISASTER}` | 85 | SoC disaster threshold (°C) |
| `{$RPI.NVME.TEMP.WARNING}` | 60 | NVMe warning threshold (°C) |
| `{$RPI.NVME.TEMP.HIGH}` | 70 | NVMe high threshold (°C) |
| `{$RPI.NVME.TEMP.DISASTER}` | 80 | NVMe disaster threshold (°C) |
| `{$RPI.NODATA}` | 10m | No-data timeout |

Override per host for different thresholds (e.g., cabinet Pis may run warmer).

## Dashboard

6-page dashboard, page rotation 10s (slideshow off by default):

1. **Overview** — model, current power, fan state, four "now" throttle indicators (red/green), decoded throttle summary, active problems
2. **Temperatures** — single full-size svggraph overlaying every discovered thermal zone
3. **NVMe** — single full-size svggraph overlaying every discovered NVMe drive
4. **Power** — power consumption graph + voltage rails overlay graph
5. **Throttle status** — decoded summary, raw bitmask, current power, and item-value tiles for all 8 throttle bits (4 "now" + 4 "since boot"), green when 0 / red when 1
6. **Performance** — CPU/GPU frequency graph + fan speed graph + current frequency / fan tiles

### Power consumption (Pi 5 only)

The `rpi.power.watts` item sums voltage x current across every rail reported by `vcgencmd pmic_read_adc` (Pi 5 PMIC). It approximates total system power downstream of the PMIC; the actual wall-plug draw is slightly higher due to PMIC efficiency. Pi 4 and earlier lack PMIC ADC monitoring and report `0`.

## Data Retention

| Category | History | Trends |
|---|---|---|
| Temperatures | 14d | 365d |
| Voltages | 14d | 365d |
| Power consumption | 14d | 365d |
| Throttle bits | 30d | 365d |
| Throttle summary | 30d | — |
| Frequencies | 7d | 90d |
| Fan state / RPM | 7d | 90d |
| Model | 1d | — |
| Master item (JSON) | — | — |

## Sources

- [Raspberry Pi vcgencmd](https://www.raspberrypi.com/documentation/computers/os.html#vcgencmd)
- [Raspberry Pi get_throttled](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled)
