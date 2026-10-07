# FlightTelemetryTools

Parse DJI drone `.SRT` subtitle telemetry into **GPX / KML** flight tracks for Google Earth, or burn an **altitude + speed HUD** into the sibling video with ffmpeg.

Most DJI models (when Video Subtitles / Captions are enabled) write a `.SRT` sidecar next to each clip. This tool reads those subtitles only — it is **not** a flight controller or airdata decoder.

**Author:** Zach Telford ([ztel42](https://github.com/ztel42))

---

## What it does

1. **Parse** real DJI `.SRT` dialects and extract lat/lon/altitude (and speed when present).
2. **Export** GPX 1.1 tracks and KML 2.2 LineString + `gx:Track` for Google Earth.
3. **Burn** a simple ASS/SSA HUD (altitude, speed, optional lat/lon) into video via `ffmpeg -vf ass=...`.

Source video and SRT files are opened **read-only**. Only the output paths you name are written.

---

## Supported SRT shapes

| Dialect | Typical models | What we read |
| --- | --- | --- |
| **Classic / Format 3 (+3b)** | Mavic 3, Air 2S/3, Mini 5 Pro, … | HTML `<font>`-wrapped lines with `SrtCnt` / `FrameCnt`, datetime, `[latitude:]` `[longitude:]` `[rel_alt: … abs_alt: …]` |
| **Bracket / Format 1** | Mini 3/4 Pro, Air 2, Mavic Air 2, … | Bracket key-value lines (same GPS keys; camera `[iso]` blocks; `gb_yaw` ignored for track export) |
| **GPS function / Format 2 (+2b)** | Mavic Pro, Phantom 4, Avata 2, Matrice 300, … | `GPS(lat,lon,alt)` / `GPS(lat,lon,altM)` |
| **Compact RTK / Format 2c** | Phantom 4 RTK / P4P lineage | `GPS (lat, lon, alt)` plus recorded `H.S Nm/s` when present |

Optional recorded speed tags also accepted when present: `H.S …m/s`, `[h_spd: …]`, `[speed: …]`.

**Tolerant of missing optional fields.** Cues with **no lat/lon** are skipped. Altitude prefers **absolute** (`abs_alt` / GPS tuple) when present, else **relative** (`rel_alt`). Speed uses a **recorded** horizontal value when the SRT has one; otherwise ground speed is **estimated** from successive GPS points and timestamps (haversine) and labelled as estimated.

---

## Requirements

- Python 3.10+ (**stdlib only** for parse / GPX / KML)
- **ffmpeg** (+ ffprobe) for the `burn` HUD command only — install via your OS package manager (`apt`, `brew`, `dnf`, …). The tool does **not** auto-install packages.
- `pytest` for tests

---

## Install

```bash
cd FlightTelemetryTools
pip install -e .
# or run without install:
PYTHONPATH=. python -m flight_telemetry --help
```

Entry points after install: `flight-telemetry` and `python -m flight_telemetry`.

---

## Usage

```bash
# Export both GPX and KML
flight-telemetry parse flight.SRT --gpx out.gpx --kml out.kml

# Same via module
python -m flight_telemetry parse flight.SRT --gpx out.gpx --kml out.kml

# Burn altitude/speed HUD (uses sibling VIDEO.SRT if --srt omitted)
flight-telemetry burn video.mp4 --srt video.SRT --out video_hud.mp4

# HUD without lat/lon line
flight-telemetry burn video.mp4 --srt video.SRT --out video_hud.mp4 --no-latlon
```

Bad input (missing file, no GPS frames, ffmpeg unavailable for burn) exits **non-zero** with a clear stderr message.

---

## Sample output

- **GPX**: one `trk` / `trkseg` of `trkpt` elements with `lat`, `lon`, `ele`, and `time`.
- **KML**: a `LineString` path plus a `gx:Track` (`when` + `gx:coord`); `altitudeMode` is `absolute` or `relativeToGround` matching the altitude source.
- **HUD video**: ASS overlay in the upper-left showing `alt: … m (abs|rel)`, `spd: … m/s (rec|est)`, and optionally lat/lon, timed to SRT cues.

---

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```

Fixtures under `tests/fixtures/` cover classic font-wrapped, bracket Mini-style, and GPS-function / H.S dialects, plus missing-GPS cues. The burn test generates a short silent lavfi MP4 (no drone footage required) and skips if ffmpeg/ffprobe are not already on PATH.

---

## Layout

```
FlightTelemetryTools/
  flight_telemetry/
    parser.py       # DJI SRT dialects
    speed.py        # haversine estimate
    export_gpx.py
    export_kml.py
    hud.py          # ASS + ffmpeg burn
    cli.py
  tests/
    fixtures/
  README.md
  pyproject.toml
  requirements.txt
```

---

## Limitations

- **Not a flight controller.** Telemetry comes from video subtitle sidecars only.
- GPS lock gaps mean skipped frames; indoor / pre-lock cues often have no coordinates.
- **Estimated speed is approximate** (GPS noise, irregular cue timing). Prefer recorded `H.S` / `[h_spd]` when the dialect provides it.
- HUD burn re-encodes video through ffmpeg; audio is copied when present.
- Does not decrypt DJI flight logs (`.txt` / DAT) — only `.SRT` subtitles.

---

## Changelog

- **Wed Oct 7, 2026 ET** — Removed silent `apt-get` auto-install of ffmpeg. HUD burn now errors clearly if ffmpeg/ffprobe are missing; install them yourself via your package manager.

---

## License

For portfolio demonstration. Use only with footage and sidecars you own or are authorized to process.
