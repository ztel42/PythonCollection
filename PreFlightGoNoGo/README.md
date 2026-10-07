# PreFlightGoNoGo

Pre-flight **go / no-go** check for recreational and professional drone ops.

Pulls the current **METAR** for nearby airports from the [aviationweather.gov Data API](https://aviationweather.gov/data/api/), the planetary **Kp index** from [NOAA SWPC](https://www.swpc.noaa.gov/content/data-access) (high Kp can degrade GPS), and computes **sunrise / sunset / civil twilight / golden hour** for your lat/lon, then prints a simple **FLY / MARGINAL / DON'T FLY** summary with reasons.

**Author:** Zach Telford ([ztel42](https://github.com/ztel42))

This is an **advisory** tool only — not a substitute for LAANC authorization, Remote ID, Part 107 judgment, or looking out the window.

---

## What it does

1. **METAR** — wind, gusts, visibility, ceiling (BKN/OVC), weather phenomena, flight category.
2. **Kp** — latest planetary K-index (geomagnetic activity → GPS scintillation risk).
3. **Sun** — sunrise, sunset, civil dawn/dusk, golden hour windows (America/New_York by default).
4. **Score** — worst factor wins → `FLY` | `MARGINAL` | `DON'T FLY`, with a text dashboard (or `--json`).

---

## Requirements

- Python **3.10+** (stdlib only at runtime: `urllib`, `zoneinfo`, `math`, `json`, `argparse`)
- Network access for **live** mode
- `pytest` for tests (offline fixtures; no live network required)

---

## Install

```bash
cd PreFlightGoNoGo
pip install -e .
# or without install:
PYTHONPATH=. python -m preflight_go_no_go --help
```

Entry points: `preflight-go-no-go` and `python -m preflight_go_no_go`.

---

## Usage

```bash
# Primary ICAO + site lat/lon (Space Coast example)
python -m preflight_go_no_go --icao KXMR --lat 28.39 --lon -80.60

# Nearest seed stations from lat/lon only (KXMR/KTTS/KCOF/…)
python -m preflight_go_no_go --lat 28.39 --lon -80.60 --stations 3

# Explicit nearby list
python -m preflight_go_no_go --icao KXMR --nearby KCOF,KTTS --lat 28.39 --lon -80.60

# Also query METARs via bbox around lat/lon
python -m preflight_go_no_go --lat 28.39 --lon -80.60 --bbox --live

# Offline fixtures (CI / demos)
python -m preflight_go_no_go --icao KXMR --lat 28.39 --lon -80.60 \
  --fixture-metar tests/fixtures/metar_vfr.json \
  --fixture-kp tests/fixtures/kp_quiet.json \
  --now 2026-10-07T13:00:00

# Machine-readable
python -m preflight_go_no_go --icao KXMR --lat 28.39 --lon -80.60 --json
```

Exit codes: `0` = FLY or MARGINAL, `1` = DON'T FLY, `2` = usage/fetch error.

---

## Data sources (APIs)

| Source | Endpoint | Notes |
| --- | --- | --- |
| **METAR** | `https://aviationweather.gov/api/data/metar?ids=KXMR,KCOF&format=json` | NOAA/NWS Aviation Weather Center Data API. Also supports `bbox=south,west,north,east`. No API key. Rate limit ~100 req/min. Docs: https://aviationweather.gov/data/api/ |
| **Kp** | `https://services.swpc.noaa.gov/json/planetary_k_index_1m.json` | NOAA SWPC 1-minute planetary K-index JSON. Latest array element used (`kp_index` / `estimated_kp`). |
| **Sun** | *(local)* | NOAA Solar Calculator style equations (Meeus). No network. Default TZ `America/New_York`. |

Station seed list (for `--lat/--lon` nearest lookup) covers Florida Space Coast: KXMR, KTTS, KCOF, KTIX, KMLB, KX21, KDAB, KORL, KMCO, KSFB.

---

## Default thresholds

All overridable via CLI (`--wind-marginal`, `--kp-nofly`, …).

| Factor | MARGINAL | DON'T FLY |
| --- | --- | --- |
| Sustained wind | ≥ **20 kt** | ≥ **25 kt** |
| Gusts | ≥ **25 kt** | ≥ **30 kt** |
| Visibility | < **5 SM** | < **3 SM** |
| Ceiling (BKN/OVC/VV) | < **1500 ft** AGL | < **500 ft** AGL |
| Weather | light precip / mist (`-RA`, `BR`, …) | thunderstorms (`TS`/`TSRA`), heavy precip (`+RA`), freezing fog/precip |
| Kp index | ≥ **5** (GPS risk elevated) | ≥ **7** (severe geomagnetic / GPS scintillation risk) |
| Daylight | outside **civil twilight** (night) | only if `--night-nofly` |

Overall verdict = **worst** factor. Clear VFR + quiet Kp + daylight → **FLY**.

---

## Sample dashboard

```
============================================================
  PRE-FLIGHT GO / NO-GO
============================================================
  Location : KXMR
  Lat/Lon  : 28.39000, -80.60000
  When     : 2026-10-07 13:00 EDT

  VERDICT  : [ FLY ]

  Factors
  -------
  [OK ] wind         FLY         sustained 8 kt (ok)
  [OK ] visibility   FLY         10+ SM (ok)
  [OK ] ceiling      FLY         no BKN/OVC ceiling (FEW)
  [OK ] weather      FLY         no significant weather
  [OK ] kp           FLY         Kp 1.33 (ok)
  [OK ] daylight     FLY         day — civil daylight (ok)
  ...
```

---

## Tests

```bash
cd PreFlightGoNoGo
pip install -e ".[dev]"   # or: pip install pytest
pytest -q
```

Tests use **offline fixtures** under `tests/fixtures/` and mock HTTP. No live network required for CI.

---

## Changelog

- **Wed Oct 7, 2026 ET** — Initial release: METAR (aviationweather.gov), Kp (NOAA SWPC), sun/golden hour, FLY/MARGINAL/DON'T FLY scoring, CLI dashboard + JSON, offline fixtures/tests.
