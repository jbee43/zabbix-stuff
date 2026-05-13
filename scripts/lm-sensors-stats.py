#!/usr/bin/env python3
"""Collect lm-sensors hardware data as JSON for Zabbix.

Requires: lm-sensors (sensors -j), Python 3.6+
Install: sudo apt install lm-sensors && sudo sensors-detect --auto
"""
import json
import re
import subprocess


def sanitize(s):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", s).strip("_")


def main():
    empty = {
        "temperatures": [], "temperature_max": [], "temperature_crit": [],
        "fans": [],
        "voltages": [], "voltage_min": [], "voltage_max": [],
        "powers": [],
    }
    try:
        result = subprocess.run(
            ["sensors", "-j"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(json.dumps(empty, separators=(",", ":")))
            return
        raw = json.loads(result.stdout)
    except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
        print(json.dumps(empty, separators=(",", ":")))
        return

    temps = []
    temp_max = []
    temp_crit = []
    fans = []
    volts = []
    volt_min = []
    volt_max = []
    powers = []

    for chip, sensors in raw.items():
        if not isinstance(sensors, dict):
            continue
        for label, readings in sensors.items():
            if label == "Adapter" or not isinstance(readings, dict):
                continue

            keys = list(readings.keys())
            sid = sanitize(f"{chip}_{label}")
            base = {"chip": chip, "label": label, "id": sid}

            temp_inputs = [k for k in keys if re.match(r"^temp\d+_input$", k)]
            if temp_inputs:
                prefix = temp_inputs[0].rsplit("_", 1)[0]
                temps.append({**base, "input": readings.get(temp_inputs[0])})
                tmax = readings.get(f"{prefix}_max")
                if tmax is not None:
                    temp_max.append({**base, "value": tmax})
                tcrit = readings.get(f"{prefix}_crit")
                if tcrit is not None:
                    temp_crit.append({**base, "value": tcrit})
                continue

            fan_inputs = [k for k in keys if re.match(r"^fan\d+_input$", k)]
            if fan_inputs:
                fans.append({**base, "input": readings.get(fan_inputs[0])})
                continue

            volt_inputs = [k for k in keys if re.match(r"^in\d+_input$", k)]
            if volt_inputs:
                prefix = volt_inputs[0].rsplit("_", 1)[0]
                volts.append({**base, "input": readings.get(volt_inputs[0])})
                vmin = readings.get(f"{prefix}_min")
                if vmin is not None:
                    volt_min.append({**base, "value": vmin})
                vmax = readings.get(f"{prefix}_max")
                if vmax is not None:
                    volt_max.append({**base, "value": vmax})
                continue

            power_inputs = [k for k in keys if re.match(r"^power\d+_input$", k)]
            if power_inputs:
                powers.append({**base, "input": readings.get(power_inputs[0])})
                continue

    print(json.dumps({
        "temperatures": temps,
        "temperature_max": temp_max,
        "temperature_crit": temp_crit,
        "fans": fans,
        "voltages": volts,
        "voltage_min": volt_min,
        "voltage_max": volt_max,
        "powers": powers,
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
