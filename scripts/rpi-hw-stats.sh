#!/bin/bash
# rpi-hw-stats.sh — Collect Raspberry Pi hardware statistics as JSON
# Requires: bash, coreutils
# Optional: vcgencmd (libraspberrypi-bin) for voltages, throttle, GPU frequency

set -euo pipefail

HAS_VCGENCMD=false
command -v vcgencmd >/dev/null 2>&1 && HAS_VCGENCMD=true

# Thermal zones
thermal="["
first=true
for zone in /sys/class/thermal/thermal_zone*; do
    [ -d "$zone" ] || continue
    num="${zone##*thermal_zone}"
    type=$(cat "$zone/type" 2>/dev/null || echo "unknown")
    temp=$(cat "$zone/temp" 2>/dev/null || echo "0")
    $first || thermal+=","
    first=false
    thermal+="{\"zone\":$num,\"type\":\"$type\",\"temp_mc\":${temp}}"
done
thermal+="]"

# Voltages (vcgencmd)
voltages="["
if $HAS_VCGENCMD; then
    first=true
    for vtype in core sdram_c sdram_i sdram_p; do
        val=$(vcgencmd measure_volts "$vtype" 2>/dev/null | grep -oP '[\d.]+' || true)
        if [ -n "$val" ]; then
            $first || voltages+=","
            first=false
            voltages+="{\"type\":\"$vtype\",\"volts\":$val}"
        fi
    done
fi
voltages+="]"

# Throttle status (hex bitmask)
throttled="0x0"
$HAS_VCGENCMD && throttled=$(vcgencmd get_throttled 2>/dev/null | grep -oP '0x[\da-fA-F]+' || echo "0x0")

# CPU frequency (kHz from sysfs)
cpu_freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo "0")
cpu_freq_max=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq 2>/dev/null || echo "0")

# GPU frequency (Hz from vcgencmd)
gpu_freq="0"
$HAS_VCGENCMD && gpu_freq=$(vcgencmd measure_clock core 2>/dev/null | grep -oP '\d+$' || echo "0")

# Fan state (Pi 5 active cooler PWM: 0-4, 255 = no fan)
fan_state=255
[ -f /sys/class/thermal/cooling_device0/cur_state ] && fan_state=$(cat /sys/class/thermal/cooling_device0/cur_state 2>/dev/null || echo "255")

# Fan RPM (Pi 5 active cooler tach via hwmon)
fan_rpm=0
for fan in /sys/class/hwmon/hwmon*/fan1_input; do
    [ -f "$fan" ] || continue
    fan_rpm=$(cat "$fan" 2>/dev/null || echo "0")
    break
done

# System power consumption (Pi 5 PMIC: sum of V*A across all rails reported by pmic_read_adc)
# Returns 0 on Pis without PMIC monitoring (Pi 4 and older).
power_watts="0"
if $HAS_VCGENCMD; then
    pmic=$(vcgencmd pmic_read_adc 2>/dev/null || true)
    if [ -n "$pmic" ]; then
        calc=$(printf '%s\n' "$pmic" | awk '
            {
                # $1 = rail name with _A or _V suffix; $2 = "current(N)=X.XXXXA" or "volt(N)=X.XXXXV"
                n = split($2, parts, "=")
                if (n < 2) next
                val = parts[2]
                unit = substr(val, length(val))
                num = substr(val, 1, length(val) - 1) + 0
                rail = $1
                suffix = substr(rail, length(rail) - 1)
                base = substr(rail, 1, length(rail) - 2)
                if (unit == "A" && suffix == "_A") curr[base] = num
                else if (unit == "V" && suffix == "_V") volt[base] = num
            }
            END {
                total = 0
                for (r in curr) if (r in volt) total += curr[r] * volt[r]
                printf "%.4f", total
            }')
        [ -n "$calc" ] && power_watts="$calc"
    fi
fi

# NVMe devices (M.2 HAT)
nvme="["
first=true
for dev in /sys/class/nvme/nvme*; do
    [ -d "$dev" ] || continue
    name=$(basename "$dev")
    temp=""
    for hwmon in "$dev"/hwmon*; do
        [ -f "$hwmon/temp1_input" ] && temp=$(cat "$hwmon/temp1_input" 2>/dev/null) && break
    done
    if [ -n "$temp" ]; then
        $first || nvme+=","
        first=false
        nvme+="{\"device\":\"$name\",\"temp_mc\":$temp}"
    fi
done
nvme+="]"

# Model
model=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "Unknown")

printf '{"model":"%s","thermal":%s,"voltages":%s,"throttled":"%s","cpu_freq_khz":%s,"cpu_freq_max_khz":%s,"gpu_freq_hz":%s,"fan_state":%s,"fan_rpm":%s,"power_watts":%s,"nvme":%s}\n' \
    "$model" "$thermal" "$voltages" "$throttled" "$cpu_freq" "$cpu_freq_max" "$gpu_freq" "$fan_state" "$fan_rpm" "$power_watts" "$nvme"
