# Linux Hardware (lm-sensors)

**Template:** `templates/linux-hw-lm-sensors.json`
**Script:** `scripts/lm-sensors-stats.py`
**Config:** `userparameters/linux-hw-lm-sensors.conf`
**Name:** Linux Hardware lm-sensors by Zabbix agent active
**Group:** Templates/Server hardware

Linux hardware monitoring via `lm-sensors`. Automatically discovers all temperature sensors, fans, voltage rails, and power sensors. Single master item collects everything as JSON every 2 minutes via `sensors -j`.

## Prerequisites

```bash
# Install lm-sensors
sudo apt install lm-sensors

# Detect hardware sensors
sudo sensors-detect --auto

# Verify output
sensors -j
```

Python 3.6+ is required for the collection script.

## Setup

```bash
sudo cp scripts/lm-sensors-stats.py /etc/zabbix/scripts/
sudo chmod +x /etc/zabbix/scripts/lm-sensors-stats.py
sudo cp userparameters/linux-hw-lm-sensors.conf /etc/zabbix/zabbix_agent2.d/
sudo systemctl restart zabbix-agent2
```

## Discovered Items (LLD)

| Discovery | Macros | Items per instance |
|---|---|---|
| Temperature sensors | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Temperature (°C) |
| Temperature max threshold | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Hardware-defined max (°C) |
| Temperature critical threshold | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Hardware-defined crit (°C) |
| Fan sensors | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Fan speed (RPM) |
| Voltage sensors | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Voltage (V) |
| Voltage min threshold | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Hardware-defined min (V) |
| Voltage max threshold | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Hardware-defined max (V) |
| Power sensors | `{#SENSOR.ID}`, `{#SENSOR.CHIP}`, `{#SENSOR.LABEL}` | Power draw (W) |

Threshold LLDs (`temperature_max`, `temperature_crit`, `voltage_min`, `voltage_max`) only discover sensors that actually report those values, so no orphan "Not supported" items are created on chips that omit them (e.g. `cpu_thermal-virtual-0`, NVMe `Sensor 1`).

## Triggers

| Trigger | Severity | Default |
|---|---|---|
| Temperature > WARNING | WARNING | 80°C |
| Temperature > HIGH | HIGH | 90°C |
| Temperature > DISASTER | DISASTER | 100°C |
| Fan speed below minimum | WARNING | 200 RPM |
| No data received | WARNING | 10m |

All temperature triggers use 5-minute average with dependency chains (DISASTER suppresses HIGH suppresses WARNING).

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$LM.TEMP.WARNING}` | 80 | Temperature warning threshold (°C) |
| `{$LM.TEMP.HIGH}` | 90 | Temperature high threshold (°C) |
| `{$LM.TEMP.DISASTER}` | 100 | Temperature disaster threshold (°C) |
| `{$LM.FAN.MIN}` | 200 | Minimum fan speed (RPM). Set to 0 for zero-RPM idle fans |
| `{$LM.NODATA}` | 10m | No-data timeout |

## Dashboard

Single **Overview** page, 2x2 grid of svggraph widgets. Each widget overlays every discovered sensor in that category, filtered by item-name wildcard:

| Position | Widget | Filter | Color |
|---|---|---|---|
| Top-left | Temperatures | `* temperature` | `FF465C` |
| Bottom-left | Voltages | `* voltage` | `FF8000` |
| Top-right | Fans | `* fan speed` | `64B5F6` |
| Bottom-right | Power | `* power` | `9C27B0` |

Filters are anchored on both sides, so threshold items (`* voltage min/max`, `* temperature max/critical`) are intentionally excluded — only the live input series overlay.

Per-instance graph prototypes (one chart per discovered sensor) are still created and accessible from *Hosts → Graphs* / *Latest data*; they just aren't pinned to the dashboard.

## Caveats

- **Raspberry Pi 5 power is not discovered here.** The Pi 5's PMIC is not exposed as a hwmon `powerN_input` device by `sensors -j`, so the lm-sensors Power LLD returns an empty list and the dashboard's Power widget stays blank. Pi 5 system-power is collected by the **Raspberry Pi** template via `vcgencmd pmic_read_adc` (item `pi.power`). Apply both templates to a Pi 5 host if you want power graphed.
- Some chips report only a subset of sensor classes (e.g. `cpu_thermal-virtual-0` exposes temperature but no max/crit thresholds). The threshold LLDs filter those out so no orphan "Not supported" items are created.

## Data Retention

| Category | History | Trends |
|---|---|---|
| Temperatures, fans, voltages, power | 14d | 365d |
| Sensor thresholds (max, crit, min) | 1d | — |
| Master item (JSON) | — | — |

## Sources

- [lm-sensors](https://github.com/lm-sensors/lm-sensors)
