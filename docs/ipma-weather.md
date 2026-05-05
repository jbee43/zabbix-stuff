# Weather (IPMA)

**Template:** `templates/ipma-weather.json`
**Name:** Weather by IPMA HTTP
**Group:** Templates

## TLDR

5-day daily weather forecast and active weather warnings for any Portuguese
region, via the [IPMA Open Data API](https://api.ipma.pt/). HTTP-only — no
agent, no script. Numeric-coded forecast/warning levels rendered through value
maps, stable per-day "today" items for actionable alerts and dashboard tiles,
calculated warning summaries that survive LLD churn, and a 5-day forecast
dashboard with at-a-glance status tiles.

## How to Use

1. **Import** `templates/ipma-weather.json` into Zabbix (`Data collection → Templates → Import`).
2. **Find the IDs** for the area you want to monitor — both come from the same JSON file:
   <https://api.ipma.pt/open-data/distrits-islands.json>
   - `globalIdLocal` → `{$IPMA.LOCATION.ID}` (forecast endpoint)
   - `idAreaAviso` → `{$IPMA.WARNING.AREA.ID}` (warning filter)
3. **Assign** the template to a host (any host — the items are HTTP, the host is just an attachment point).
4. **(Optional)** Tune the threshold and interval macros listed below.

The template ships with Lisbon defaults (`1110600` / `LSB`) so it works out of the box for testing.

## Data Sources

| Endpoint                                                                                  | Used for                                        |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/{globalIdLocal}.json`    | 5-day daily forecast (master + LLD + today)     |
| `https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json`                       | Next-3-day warnings (master + LLD, area-filtered) |
| `https://api.ipma.pt/open-data/weather-type-classe.json`                                  | Reference for the `IPMA weather type` value map |
| `https://api.ipma.pt/open-data/wind-speed-daily-classe.json`                              | Reference for the `IPMA wind speed class` value map |

## Items

### Master items

| Item                | Key                  | Interval                                  | Stored?               |
| ------------------- | -------------------- | ----------------------------------------- | --------------------- |
| Forecast: get raw   | `ipma.forecast.raw`  | `{$IPMA.FORECAST.INTERVAL}` (default 30m) | No (history/trends 0) |
| Warnings: get raw   | `ipma.warning.raw`   | `{$IPMA.WARNING.INTERVAL}` (default 10m)  | No (history/trends 0) |

Both apply `DISCARD_UNCHANGED_HEARTBEAT` so dependents only update when the upstream JSON actually changes.

### "Today" snapshot items (stable, dashboard-friendly)

A helper item, `ipma.forecast.today.raw`, extracts today's forecast object from the master 5-day array (matching `forecastDate` against the agent's UTC date, falling back to `data[0]` if today is not present — which can happen when the API has not yet rolled to the new day's bulletin). The following items depend on it for at-a-glance dashboard tiles and actionable alerts (one trigger per metric, regardless of how many days the forecast spans):

| Item                              | Key                                       | Type     | Notes                                              |
| --------------------------------- | ----------------------------------------- | -------- | -------------------------------------------------- |
| Forecast today: rain probability  | `ipma.forecast.today.rain`                | float    | %                                                  |
| Forecast today: temperature, max  | `ipma.forecast.today.temperature.max`     | float    | °C                                                 |
| Forecast today: temperature, min  | `ipma.forecast.today.temperature.min`     | float    | °C                                                 |
| Forecast today: weather type      | `ipma.forecast.today.weather.type`        | unsigned | IPMA ID 0–30 + `IPMA weather type` value map       |
| Forecast today: wind direction    | `ipma.forecast.today.wind.direction`      | char     | N, NE, E, …                                        |
| Forecast today: wind speed class  | `ipma.forecast.today.wind.speed`          | unsigned | 1–4 + `IPMA wind speed class` value map            |

### Forecast item prototypes (per `{#DATE}`, via LLD — 5 days)

Used for forecast graphs (no triggers — alerts live on the today items). Lets you see the trend across the 5-day window without spamming five copies of the same alert when a heatwave or storm is forecast.

| Prototype                          | Key                                              | Type     |
| ---------------------------------- | ------------------------------------------------ | -------- |
| Forecast {#DATE}: rain probability | `ipma.forecast.rain[{#DATE}]`                    | float    |
| Forecast {#DATE}: temperature, max | `ipma.forecast.temperature.max[{#DATE}]`         | float    |
| Forecast {#DATE}: temperature, min | `ipma.forecast.temperature.min[{#DATE}]`         | float    |
| Forecast {#DATE}: weather type     | `ipma.forecast.weather.type[{#DATE}]`            | unsigned |
| Forecast {#DATE}: wind direction   | `ipma.forecast.wind.direction[{#DATE}]`          | char     |
| Forecast {#DATE}: wind speed class | `ipma.forecast.wind.speed[{#DATE}]`              | unsigned |

### Warning item prototypes (per `{#WARNING.TYPE}`, via LLD, filtered by `{$IPMA.WARNING.AREA.ID}`)

| Prototype                                | Key                                          | Type     | Notes                                                             |
| ---------------------------------------- | -------------------------------------------- | -------- | ----------------------------------------------------------------- |
| Warning {#WARNING.TYPE}: awareness level | `ipma.warning.awareness[{#WARNING.TYPE}]`    | unsigned | 0–3 (green/yellow/orange/red) + `IPMA awareness level` value map  |
| Warning {#WARNING.TYPE}: start time      | `ipma.warning.starttime[{#WARNING.TYPE}]`    | unsigned | unixtime, parsed as UTC                                           |
| Warning {#WARNING.TYPE}: end time        | `ipma.warning.endtime[{#WARNING.TYPE}]`      | unsigned | unixtime, parsed as UTC                                           |
| Warning {#WARNING.TYPE}: text            | `ipma.warning.text[{#WARNING.TYPE}]`         | text     | Description issued by IPMA (Portuguese)                           |

### Warning summary items (calculated, stable across LLD churn)

These summarise the per-category awareness items into a single number per host, useful as dashboard tiles and as the source of "the area is under warning" automations. Both fall back to `0` (via `CHECK_NOT_SUPPORTED → custom value 0`) when no warning items have been discovered yet.

| Item                          | Key                            | Formula                                                                                  |
| ----------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------- |
| Warnings: max awareness level | `ipma.warning.summary.max`     | `max(last_foreach(/<host>/ipma.warning.awareness[*]))`                                   |
| Warnings: active count        | `ipma.warning.summary.count`   | `count(last_foreach(/<host>/ipma.warning.awareness[*]),"ge","1")`                        |

## Triggers

### Today triggers (actionable, one alert per metric)

| Trigger                                     | Severity | Condition                                                            |
| ------------------------------------------- | -------- | -------------------------------------------------------------------- |
| Today: rain probability above threshold     | INFO     | rain prob > `{$IPMA.RAIN.PROB.WARN}`                                 |
| Today: temperature max. above threshold     | AVERAGE  | tMax > `{$IPMA.TEMP.MAX.HIGH}`                                       |
| Today: temperature min. below threshold     | AVERAGE  | tMin < `{$IPMA.TEMP.MIN.LOW}`                                        |
| Today: wind is strong (or stronger)         | WARNING  | wind class >= `{$IPMA.WIND.STRONG}` (depends on very-strong trigger) |
| Today: wind is very strong                  | AVERAGE  | wind class >= `{$IPMA.WIND.VERY.STRONG}`                             |

### Warning triggers (per warning category)

Active iff the awareness level meets the threshold **and** `now()` is within the IPMA-issued `[startTime, endTime]` window.

| Trigger                                  | Severity | Condition (awareness >=) | Suppressed by |
| ---------------------------------------- | -------- | ------------------------ | ------------- |
| Warning {#WARNING.TYPE} active: yellow   | WARNING  | 1                        | orange/red    |
| Warning {#WARNING.TYPE} active: orange   | AVERAGE  | 2                        | red           |
| Warning {#WARNING.TYPE} active: red      | HIGH     | 3                        | —             |

### Availability triggers

| Trigger                                              | Severity | Condition                          |
| ---------------------------------------------------- | -------- | ---------------------------------- |
| IPMA forecast: no data for `{$IPMA.FORECAST.NODATA}` | WARNING  | nodata over the configured window |
| IPMA warnings: no data for `{$IPMA.WARNING.NODATA}`  | WARNING  | nodata over the configured window |

## Macros

| Macro                       | Default   | Description                                                                                  |
| --------------------------- | --------- | -------------------------------------------------------------------------------------------- |
| `{$IPMA.LOCATION.ID}`       | `1110600` | IPMA `globalIdLocal` for the forecast endpoint (default = Lisboa).                           |
| `{$IPMA.WARNING.AREA.ID}`   | `LSB`     | IPMA `idAreaAviso` for filtering warnings (default = Lisboa).                                |
| `{$IPMA.FORECAST.INTERVAL}` | `30m`     | Forecast polling interval (IPMA publishes ~2x/day; lower wastes calls).                      |
| `{$IPMA.WARNING.INTERVAL}`  | `10m`     | Warnings polling interval; also the period used by the warning summary calculations.         |
| `{$IPMA.FORECAST.NODATA}`   | `2h`      | No-data threshold for the forecast master item.                                              |
| `{$IPMA.WARNING.NODATA}`    | `30m`     | No-data threshold for the warnings master item.                                              |
| `{$IPMA.RAIN.PROB.WARN}`    | `50`      | Rain probability (%) threshold for the today INFO trigger and the dashboard rain-tile color. |
| `{$IPMA.TEMP.MAX.HIGH}`     | `40`      | Maximum-temperature (°C) threshold for the today AVERAGE trigger and the temp-max tile.      |
| `{$IPMA.TEMP.MIN.LOW}`      | `1`       | Minimum-temperature (°C) threshold for the today AVERAGE trigger.                            |
| `{$IPMA.WIND.STRONG}`       | `3`       | Wind speed class threshold for the WARNING-severity trigger and the yellow tile color.       |
| `{$IPMA.WIND.VERY.STRONG}`  | `4`       | Wind speed class threshold for the AVERAGE-severity trigger and the red tile color.          |

## Value maps

| Name                    | Domain | Mapping                                              |
| ----------------------- | ------ | ---------------------------------------------------- |
| IPMA awareness level    | 0–3    | Green (no warning), Yellow, Orange, Red              |
| IPMA wind speed class   | 1–4    | Weak, Moderate, Strong, Very strong                  |
| IPMA weather type       | 0–30   | IPMA's full daily weather-type classification (English) |

## Dashboard

`Weather by IPMA HTTP` (single page `Overview`):

- **Row 1 (status tiles)**: max awareness level (green→red thresholds), active warnings count, today max temperature (red threshold = `{$IPMA.TEMP.MAX.HIGH}`), today min temperature.
- **Row 2 (today snapshot)**: today rain probability (blue threshold = `{$IPMA.RAIN.PROB.WARN}`), today weather type, today wind speed class (yellow/red at `{$IPMA.WIND.STRONG}` / `{$IPMA.WIND.VERY.STRONG}`), today wind direction.
- **Row 3 (5-day temperatures)**: graph prototype, 3 columns × 2 rows.
- **Row 4 (5-day rain probabilities)**: graph prototype, 3 columns × 2 rows.

All widgets refresh at 30s.

## Data Retention

| Category                                      | History | Trends |
| --------------------------------------------- | ------- | ------ |
| Master items (raw JSON)                       | 0       | 0      |
| `ipma.forecast.today.raw` (helper)            | 0       | 0      |
| Today numeric items                           | 7d      | 90d    |
| Today text/discrete items                     | 7d      | 0      |
| Forecast LLD numeric items                    | 7d      | 90d    |
| Forecast LLD text/discrete items              | 7d      | 0      |
| Warning awareness                             | 14d     | 365d   |
| Warning start/end time                        | 14d     | 0      |
| Warning text                                  | 14d     | 0      |
| Warning summary items (calculated)            | 14d     | 365d   |

## Design Notes

- **Two-tier forecast layout.** Stable per-metric "today" items drive triggers and dashboard tiles (one alert per metric, addressable by Item-value widgets). LLD-discovered per-day items drive 5-day graphs only — no triggers, so a multi-day heatwave doesn't fire five identical alerts.
- **Warning summary calculations.** `max(last_foreach(...))` and `count_foreach(...)` over the per-category LLD items give stable, single-host signals that survive when individual warning items churn (created/deleted as IPMA issues/expires warnings). `CHECK_NOT_SUPPORTED → custom value 0` keeps them defined when no warning items exist yet.
- **Numeric encoding for ordinal data.** Awareness level (`green`→0 … `red`→3), wind speed class (1–4) and weather type (0–30) are stored as integers and rendered through value maps. Triggers and dashboard thresholds use numeric comparisons so they are stable across IPMA copy edits.
- **UTC-safe time parsing.** IPMA returns `startTime`/`endTime` as ISO-8601 without a timezone (e.g. `2026-04-27T13:00:00`). The template appends `Z` if missing before parsing, so warning windows are evaluated correctly regardless of the Zabbix server's timezone.
- **Heartbeat de-duplication.** Master items use `DISCARD_UNCHANGED_HEARTBEAT` (6h forecast / 1h warnings) so dependent items only update when the upstream JSON actually changes — saving history writes when IPMA returns the same data twice.
- **Discovery filter via the same `idAreaAviso`** the user already configured for warnings — no second list to keep in sync.

## Sources

- [IPMA Open Data](https://api.ipma.pt/)
- [IPMA `distrits-islands` (location & area IDs)](https://api.ipma.pt/open-data/distrits-islands.json)
- [Zabbix HTTP agent](https://www.zabbix.com/documentation/7.2/en/manual/config/items/itemtypes/http)
- [Zabbix calculated items / foreach functions](https://www.zabbix.com/documentation/7.2/en/manual/config/items/itemtypes/calculated)
