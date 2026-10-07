from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from preflight_go_no_go.kp import parse_kp_json
from preflight_go_no_go.metar import parse_metar_list
from preflight_go_no_go.models import Thresholds, Verdict
from preflight_go_no_go.scoring import evaluate
from preflight_go_no_go.sun import compute_sun_times


def _day_now():
    return datetime(2026, 10, 7, 13, 0, tzinfo=ZoneInfo("America/New_York"))


def test_vfr_quiet_is_fly(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_vfr.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_quiet.json").read_text()))
    primary = next(m for m in metars if m.icao == "KXMR")
    sun = compute_sun_times(28.39, -80.60, when=_day_now())
    report = evaluate(
        primary, [m for m in metars if m.icao != "KXMR"], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=_day_now(),
    )
    assert report.verdict == Verdict.FLY


def test_mvfr_rain_is_marginal(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_mvfr.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_quiet.json").read_text()))
    primary = next(m for m in metars if m.icao == "KXMR")
    sun = compute_sun_times(28.39, -80.60, when=_day_now())
    report = evaluate(
        primary, [], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=_day_now(),
    )
    assert report.verdict == Verdict.MARGINAL
    weather = next(f for f in report.factors if f.name == "weather")
    assert weather.verdict == Verdict.MARGINAL


def test_thunderstorm_is_dont_fly(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_thunderstorm.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_quiet.json").read_text()))
    sun = compute_sun_times(28.39, -80.60, when=_day_now())
    report = evaluate(
        metars[0], [], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=_day_now(),
    )
    assert report.verdict == Verdict.DONT_FLY


def test_kp_storm_dont_fly_even_in_vfr(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_vfr.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_storm.json").read_text()))
    primary = next(m for m in metars if m.icao == "KXMR")
    sun = compute_sun_times(28.39, -80.60, when=_day_now())
    report = evaluate(
        primary, [], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=_day_now(),
    )
    assert report.verdict == Verdict.DONT_FLY
    kp_f = next(f for f in report.factors if f.name == "kp")
    assert kp_f.verdict == Verdict.DONT_FLY


def test_kp_marginal(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_vfr.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_marginal.json").read_text()))
    primary = next(m for m in metars if m.icao == "KXMR")
    sun = compute_sun_times(28.39, -80.60, when=_day_now())
    report = evaluate(
        primary, [], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=_day_now(),
    )
    assert report.verdict == Verdict.MARGINAL


def test_night_is_marginal_by_default(fixtures_dir: Path):
    metars = parse_metar_list(json.loads((fixtures_dir / "metar_vfr.json").read_text()))
    kp = parse_kp_json(json.loads((fixtures_dir / "kp_quiet.json").read_text()))
    primary = next(m for m in metars if m.icao == "KXMR")
    night = datetime(2026, 10, 7, 23, 0, tzinfo=ZoneInfo("America/New_York"))
    sun = compute_sun_times(28.39, -80.60, when=night)
    report = evaluate(
        primary, [], kp, sun, Thresholds(),
        location_label="KXMR", lat=28.39, lon=-80.60, generated_at=night,
    )
    assert report.verdict == Verdict.MARGINAL
    day_f = next(f for f in report.factors if f.name == "daylight")
    assert day_f.verdict == Verdict.MARGINAL
