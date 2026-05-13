# EVE Online

**Template:** `templates/eve-online.json`
**Name:** EVE Online by HTTP
**Group:** Templates

EVE Online game monitoring via public APIs. Tracks Tranquility status (description, VIP mode, last server start), player count, PLEX & Large Skill Injector average prices, active incursions and sovereignty campaigns, and Faction Warfare per-faction stats.

No agent required — uses HTTP agent items.

> PLEX has used a single global market since the 2018 PLEX Vault migration — there are no regional PLEX orders. Market prices come from ESI `/markets/prices/`, which returns CCP-calculated cross-region averages (smoothed, not real-time best ask). The same endpoint covers regional commodities like Skill Injectors.

## Data Sources

- ESI API (`esi.evetech.net`): `/status`, `/markets/prices/`, `/incursions/`, `/sovereignty/campaigns/`, `/fw/stats/`
- EVE status page (`status.eveonline.com`): public status description (separate from ESI; used as a sanity check)

## Setup

1. Import `templates/eve-online.json` in Zabbix UI
2. Assign template to any host (no agent needed, HTTP agent items)

## Items

Master items collect raw JSON; dependent items extract individual metrics via JSONPATH or JS preprocessing. This minimises HTTP requests (one call to ESI `/status` populates 3 items; one call to ESI `/markets/prices/` populates both PLEX and Skill Injector).

| Item | Type | Interval | Description |
|---|---|---|---|
| ESI status raw | HTTP master | 5m | Raw `/status` response (TEXT, history 0) |
| Player count | Dependent | — | Tranquility online players |
| Server start time (last TQ tick) | Dependent | — | Unix timestamp of last server startup |
| VIP mode | Dependent | — | 0 = normal, 1 = login restricted |
| Tranquility status description | HTTP agent | 5m | Status string from public status page |
| Market prices raw | HTTP master | 30m | Raw ESI `/markets/prices/` (TEXT, history 0; CCP cache 1h) |
| PLEX price | Dependent | — | Global average price, ISK |
| Large Skill Injector price | Dependent | — | Cross-region average price, ISK |
| Active incursions | HTTP agent | 30m | Count of active incursions across New Eden |
| Active sovereignty campaigns | HTTP agent | 30m | Count of active SOV campaigns |
| Faction Warfare stats raw | HTTP master | 30m | Raw `/fw/stats` response (TEXT, history 0) |
| Faction Warfare: `<faction>` pilots | Dependent | — | Per-faction enlisted pilots (4 items) |
| Faction Warfare: `<faction>` systems controlled | Dependent | — | Per-faction warzone systems (4 items) |
| Faction Warfare: `<faction>` kills (yesterday) | Dependent | — | Per-faction daily kills (4 items, resets daily) |
| Faction Warfare: `<faction>` victory points (yesterday) | Dependent | — | Per-faction daily VP (4 items, resets daily) |

Factions: Amarr Empire (500003), Caldari State (500001), Gallente Federation (500004), Minmatar Republic (500002).

## Triggers

| Trigger | Severity | Condition |
|---|---|---|
| No data from ESI `/status` | HIGH | nodata > `{$EVE.NODATA}` |
| No data from ESI `/fw/stats` | AVERAGE | nodata > `{$EVE.NODATA}` |
| No data from ESI `/markets/prices/` | AVERAGE | nodata > `{$EVE.NODATA}` |
| Tranquility status not operational | HIGH | last() ≠ "All Systems Operational" (excludes 11:00–11:30 UTC daily downtime) |
| Tranquility is in VIP mode | WARNING | last() = 1 |
| PLEX price below threshold | INFO | last() < `{$PLEX.PRICE.MIN}` ISK |
| Large Skill Injector price below threshold | INFO | last() < `{$EVE.SKILL_INJECTOR.PRICE.MIN}` ISK |

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$EVE.NODATA}` | `1h` | No-data timeout for master HTTP items |
| `{$EVE.SKILL_INJECTOR.PRICE.MIN}` | `700000000` | Minimum Large Skill Injector price (ISK) |
| `{$PLEX.PRICE.MIN}` | `4500000` | Minimum PLEX price (ISK) |

## Dashboard

Two-page dashboard:

- **Overview**: status text, VIP / last TQ tick / incursions / sov campaigns small widgets, player count graph, PLEX & Skill Injector price graphs side-by-side
- **Faction Warfare**: 2x2 grid of overlay graphs (systems controlled, pilots, kills yesterday, VP yesterday) with faction colors — Amarr `#FFB300`, Caldari `#1976D2`, Gallente `#43A047`, Minmatar `#D32F2F`

## Data Retention

| Category | History | Trends |
|---|---|---|
| Master items (raw JSON) | 0 | 0 |
| Status description | 7d | — |
| Player count, prices | 14d | 365d |
| VIP mode, uptime, incursions, sov, FW per-faction | 30d | 365d |

## Sources

- [EVE ESI API](https://esi.evetech.net/ui/) — including `/markets/prices/` for global aggregates
- [Tranquility status page](https://status.eveonline.com/)
