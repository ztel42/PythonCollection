"""CLI for Pre-Flight Go/No-Go."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence
from zoneinfo import ZoneInfo

from . import __version__
from .fetch import (
    fetch_kp,
    fetch_metars,
    fetch_metars_bbox,
    load_kp_fixture,
    load_metars_fixture,
)
from .models import GoNoGoReport, Thresholds, Verdict
from .scoring import evaluate
from .stations import icao_list_from_latlon, pick_primary
from .sun import compute_sun_times


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="preflight-go-no-go",
        description=(
            "Pre-flight go/no-go: METAR (aviationweather.gov), "
            "Kp (NOAA SWPC), sunrise/sunset/golden hour → FLY / MARGINAL / DON'T FLY."
        ),
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--icao", metavar="ICAO", help="Primary METAR station (e.g. KXMR)")
    p.add_argument(
        "--nearby",
        metavar="ICAO,ICAO",
        help="Comma-separated nearby stations to include (default: auto from --lat/--lon)",
    )
    p.add_argument("--lat", type=float, help="Site latitude (decimal degrees)")
    p.add_argument("--lon", type=float, help="Site longitude (decimal degrees)")
    p.add_argument(
        "--stations",
        type=int,
        default=3,
        help="How many nearest seed stations when using --lat/--lon (default: 3)",
    )
    p.add_argument(
        "--tz",
        default="America/New_York",
        help="IANA timezone for sun times (default: America/New_York)",
    )
    p.add_argument(
        "--bbox",
        action="store_true",
        help="Live mode: also query METARs via bbox around --lat/--lon",
    )
    p.add_argument(
        "--fixture-metar",
        metavar="PATH",
        help="Load METARs from JSON fixture (offline / tests)",
    )
    p.add_argument(
        "--fixture-kp",
        metavar="PATH",
        help="Load Kp from JSON fixture (offline / tests)",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Force live HTTP fetch (default when no fixtures given)",
    )
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    p.add_argument(
        "--now",
        metavar="ISO",
        help="Override 'now' for sun/daylight (ISO 8601, aware or naive→tz)",
    )

    # Threshold overrides
    g = p.add_argument_group("thresholds")
    g.add_argument("--wind-marginal", type=float, default=None, metavar="KT")
    g.add_argument("--wind-nofly", type=float, default=None, metavar="KT")
    g.add_argument("--gust-marginal", type=float, default=None, metavar="KT")
    g.add_argument("--gust-nofly", type=float, default=None, metavar="KT")
    g.add_argument("--vis-marginal", type=float, default=None, metavar="SM")
    g.add_argument("--vis-nofly", type=float, default=None, metavar="SM")
    g.add_argument("--ceiling-marginal", type=float, default=None, metavar="FT")
    g.add_argument("--ceiling-nofly", type=float, default=None, metavar="FT")
    g.add_argument("--kp-marginal", type=float, default=None)
    g.add_argument("--kp-nofly", type=float, default=None)
    g.add_argument(
        "--night-nofly",
        action="store_true",
        help="Treat night (outside civil twilight) as DON'T FLY instead of MARGINAL",
    )
    return p


def _thresholds_from_args(args: argparse.Namespace) -> Thresholds:
    t = Thresholds()
    if args.wind_marginal is not None:
        t.wind_marginal_kt = args.wind_marginal
    if args.wind_nofly is not None:
        t.wind_nofly_kt = args.wind_nofly
    if args.gust_marginal is not None:
        t.gust_marginal_kt = args.gust_marginal
    if args.gust_nofly is not None:
        t.gust_nofly_kt = args.gust_nofly
    if args.vis_marginal is not None:
        t.vis_marginal_sm = args.vis_marginal
    if args.vis_nofly is not None:
        t.vis_nofly_sm = args.vis_nofly
    if args.ceiling_marginal is not None:
        t.ceiling_marginal_ft = args.ceiling_marginal
    if args.ceiling_nofly is not None:
        t.ceiling_nofly_ft = args.ceiling_nofly
    if args.kp_marginal is not None:
        t.kp_marginal = args.kp_marginal
    if args.kp_nofly is not None:
        t.kp_nofly = args.kp_nofly
    if args.night_nofly:
        t.night_is_nofly = True
        t.night_is_marginal = False
    return t


def _parse_now(raw: Optional[str], tz_name: str) -> datetime:
    tz = ZoneInfo(tz_name)
    if not raw:
        return datetime.now(tz)
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def _resolve_icaos(args: argparse.Namespace) -> List[str]:
    icaos: List[str] = []
    if args.icao:
        icaos.append(args.icao.strip().upper())
    if args.nearby:
        icaos.extend(x.strip().upper() for x in args.nearby.split(",") if x.strip())
    if args.lat is not None and args.lon is not None and not args.nearby:
        for code in icao_list_from_latlon(args.lat, args.lon, n=args.stations):
            if code not in icaos:
                icaos.append(code)
    # Dedupe preserving order
    seen = set()
    out: List[str] = []
    for c in icaos:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def run_check(args: argparse.Namespace) -> GoNoGoReport:
    thresholds = _thresholds_from_args(args)
    now = _parse_now(args.now, args.tz)
    icaos = _resolve_icaos(args)

    use_fixtures = bool(args.fixture_metar or args.fixture_kp)
    if not use_fixtures and not args.live:
        # Default to live when no fixtures
        args.live = True

    metars = []
    if args.fixture_metar:
        metars = load_metars_fixture(Path(args.fixture_metar))
    elif args.live:
        if icaos:
            metars = fetch_metars(icaos)
        if args.bbox and args.lat is not None and args.lon is not None:
            extra = fetch_metars_bbox(args.lat, args.lon)
            have = {m.icao for m in metars}
            metars.extend(m for m in extra if m.icao not in have)
        if not metars and args.lat is not None and args.lon is not None:
            metars = fetch_metars_bbox(args.lat, args.lon)

    kp = None
    if args.fixture_kp:
        kp = load_kp_fixture(Path(args.fixture_kp))
    elif args.live:
        kp = fetch_kp()

    primary, nearby = pick_primary(
        metars,
        preferred_icao=args.icao,
        lat=args.lat,
        lon=args.lon,
    )

    # Location for sun: explicit lat/lon, else primary METAR coords
    lat = args.lat
    lon = args.lon
    if lat is None and primary and primary.lat is not None:
        lat = primary.lat
    if lon is None and primary and primary.lon is not None:
        lon = primary.lon

    sun = None
    if lat is not None and lon is not None:
        sun = compute_sun_times(lat, lon, when=now, tz_name=args.tz)

    if args.icao:
        label = args.icao.upper()
    elif lat is not None and lon is not None:
        label = f"{lat:.4f},{lon:.4f}"
    else:
        label = "unknown"

    return evaluate(
        primary,
        nearby,
        kp,
        sun,
        thresholds,
        location_label=label,
        lat=lat,
        lon=lon,
        generated_at=now,
    )


def format_dashboard(report: GoNoGoReport) -> str:
    lines: List[str] = []
    bar = "=" * 60
    lines.append(bar)
    lines.append("  PRE-FLIGHT GO / NO-GO")
    lines.append(bar)
    lines.append(f"  Location : {report.location_label}")
    if report.lat is not None and report.lon is not None:
        lines.append(f"  Lat/Lon  : {report.lat:.5f}, {report.lon:.5f}")
    lines.append(
        f"  When     : {report.generated_at.strftime('%Y-%m-%d %H:%M %Z')}"
    )
    lines.append("")

    badge = {
        Verdict.FLY: "[ FLY ]",
        Verdict.MARGINAL: "[ MARGINAL ]",
        Verdict.DONT_FLY: "[ DON'T FLY ]",
    }[report.verdict]
    lines.append(f"  VERDICT  : {badge}")
    lines.append("")

    lines.append("  Factors")
    lines.append("  -------")
    for f in report.factors:
        mark = {
            Verdict.FLY: "OK ",
            Verdict.MARGINAL: "!! ",
            Verdict.DONT_FLY: "XX ",
        }[f.verdict]
        lines.append(f"  [{mark}] {f.name:12s} {f.verdict.value:10s}  {f.detail}")

    if report.primary_metar:
        m = report.primary_metar
        lines.append("")
        lines.append(f"  Primary METAR  {m.icao}  {m.name}")
        if m.raw:
            lines.append(f"    {m.raw}")
        bits = []
        if m.wind_kt is not None:
            gust = f"G{m.gust_kt:.0f}" if m.gust_kt is not None else ""
            wdir = f"{m.wind_dir:03d}" if m.wind_dir is not None else "VRB"
            bits.append(f"wind {wdir}@{m.wind_kt:.0f}{gust}KT")
        if m.vis_sm is not None:
            bits.append(f"vis {m.vis_sm:g}SM")
        if m.ceiling_ft is not None:
            bits.append(f"cig {m.ceiling_ft}ft")
        if m.wx_string:
            bits.append(f"wx {m.wx_string}")
        if m.flt_cat:
            bits.append(f"cat {m.flt_cat}")
        if bits:
            lines.append("    " + " | ".join(bits))

    if report.nearby_metars:
        lines.append("")
        lines.append("  Nearby")
        for m in report.nearby_metars[:5]:
            wx = m.wx_string or "-"
            cig = f"{m.ceiling_ft}ft" if m.ceiling_ft is not None else "n/a"
            wind = f"{m.wind_kt:.0f}kt" if m.wind_kt is not None else "?"
            lines.append(f"    {m.icao:4s}  wind {wind:4s}  cig {cig:7s}  wx {wx}")

    if report.kp:
        est = (
            f" (est {report.kp.estimated_kp:g})"
            if report.kp.estimated_kp is not None
            else ""
        )
        lines.append("")
        lines.append(
            f"  Kp index : {report.kp.kp_index:g}{est}  @ {report.kp.time_tag}"
        )

    if report.sun:
        s = report.sun
        fmt = "%H:%M %Z"
        lines.append("")
        lines.append(f"  Sun ({s.timezone} / {s.date_local})  phase={s.phase}")
        lines.append(
            f"    civil dawn {s.civil_dawn.strftime(fmt)}   "
            f"sunrise {s.sunrise.strftime(fmt)}"
        )
        lines.append(
            f"    golden AM→ {s.golden_morning_end.strftime(fmt)}   "
            f"golden PM← {s.golden_evening_start.strftime(fmt)}"
        )
        lines.append(
            f"    sunset     {s.sunset.strftime(fmt)}   "
            f"civil dusk {s.civil_dusk.strftime(fmt)}"
        )

    lines.append("")
    lines.append(
        "  Advisory only — not a substitute for LAANC, Remote ID, "
        "or your own go/no-go judgment."
    )
    lines.append(bar)
    return "\n".join(lines)


def report_to_dict(report: GoNoGoReport) -> dict:
    def dt(x):
        return x.isoformat() if x is not None else None

    return {
        "verdict": report.verdict.value,
        "location": report.location_label,
        "lat": report.lat,
        "lon": report.lon,
        "generated_at": dt(report.generated_at),
        "factors": [
            {"name": f.name, "verdict": f.verdict.value, "detail": f.detail}
            for f in report.factors
        ],
        "primary_metar": None
        if not report.primary_metar
        else {
            "icao": report.primary_metar.icao,
            "raw": report.primary_metar.raw,
            "wind_kt": report.primary_metar.wind_kt,
            "gust_kt": report.primary_metar.gust_kt,
            "vis_sm": report.primary_metar.vis_sm,
            "ceiling_ft": report.primary_metar.ceiling_ft,
            "wx": report.primary_metar.wx_string,
            "flt_cat": report.primary_metar.flt_cat,
        },
        "nearby": [m.icao for m in report.nearby_metars],
        "kp": None
        if not report.kp
        else {
            "kp_index": report.kp.kp_index,
            "estimated_kp": report.kp.estimated_kp,
            "time_tag": report.kp.time_tag,
        },
        "sun": None
        if not report.sun
        else {
            "timezone": report.sun.timezone,
            "sunrise": dt(report.sun.sunrise),
            "sunset": dt(report.sun.sunset),
            "civil_dawn": dt(report.sun.civil_dawn),
            "civil_dusk": dt(report.sun.civil_dusk),
            "golden_morning_end": dt(report.sun.golden_morning_end),
            "golden_evening_start": dt(report.sun.golden_evening_start),
            "phase": report.sun.phase,
            "is_daylight": report.sun.is_daylight,
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.icao and (args.lat is None or args.lon is None) and not args.fixture_metar:
        parser.error("Provide --icao and/or --lat/--lon (or --fixture-metar for offline)")

    if (args.lat is None) ^ (args.lon is None):
        parser.error("Provide both --lat and --lon together")

    try:
        report = run_check(args)
    except Exception as exc:  # noqa: BLE001 — surface as CLI error
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        print(format_dashboard(report))

    if report.verdict == Verdict.DONT_FLY:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
