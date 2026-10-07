"""Sunrise, sunset, civil twilight, and golden hour via NOAA solar calculator.

Algorithm adapted from NOAA Solar Calculator / Jean Meeus equations
(public domain style; no external dependency). Times are timezone-aware.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import SunTimes

# Civil twilight sun altitude (degrees)
_CIVIL_ALT = -6.0
# Geometric sunrise/set (upper limb approx with refraction) — NOAA uses -0.833°
_RISE_ALT = -0.833


def _julian_day(d: date) -> float:
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    return d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _solar_noon_and_hour_angle(
    d: date,
    lat: float,
    lon: float,
    altitude_deg: float,
) -> tuple[float, float | None]:
    """Return (solar noon as Julian centuries offset minutes from 0 UTC day, hour angle deg or None)."""
    jd = _julian_day(d)
    # Julian century from J2000.0 at 0h UTC approx mid-day correction applied later
    t = (jd - 2451545.0) / 36525.0

    # Geometric mean longitude / anomaly (degrees)
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    m_rad = math.radians(m)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    c = (
        math.sin(m_rad) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * m_rad) * (0.019993 - 0.000101 * t)
        + math.sin(3 * m_rad) * 0.000289
    )
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    lam = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))

    decl = math.degrees(
        math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam)))
    )

    y = math.tan(math.radians(eps / 2)) ** 2
    eqtime = 4 * math.degrees(
        y * math.sin(2 * math.radians(l0))
        - 2 * e * math.sin(m_rad)
        + 4 * e * y * math.sin(m_rad) * math.cos(2 * math.radians(l0))
        - 0.5 * y * y * math.sin(4 * math.radians(l0))
        - 1.25 * e * e * math.sin(2 * m_rad)
    )

    # Solar noon in minutes from UTC midnight for this longitude
    solar_noon_min = 720 - 4 * lon - eqtime

    lat_r = math.radians(lat)
    decl_r = math.radians(decl)
    cos_ha = (
        math.cos(math.radians(90.0 - altitude_deg))
        - math.sin(lat_r) * math.sin(decl_r)
    ) / (math.cos(lat_r) * math.cos(decl_r))

    if cos_ha < -1.0 or cos_ha > 1.0:
        return solar_noon_min, None
    ha = math.degrees(math.acos(cos_ha))
    return solar_noon_min, ha


def _utc_from_minutes(d: date, minutes: float) -> datetime:
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    # minutes may be outside 0..1440 near poles/date line — clamp via timedelta
    return base + timedelta(minutes=minutes)


def compute_sun_times(
    lat: float,
    lon: float,
    when: datetime | None = None,
    tz_name: str = "America/New_York",
) -> SunTimes:
    """Compute sun / twilight / golden hour for lat/lon on the local calendar day of `when`."""
    tz = ZoneInfo(tz_name)
    if when is None:
        when = datetime.now(tz)
    elif when.tzinfo is None:
        when = when.replace(tzinfo=tz)
    else:
        when = when.astimezone(tz)

    local_day = when.date()

    noon_min, ha_rise = _solar_noon_and_hour_angle(local_day, lat, lon, _RISE_ALT)
    _, ha_civil = _solar_noon_and_hour_angle(local_day, lat, lon, _CIVIL_ALT)

    if ha_rise is None:
        # Polar day/night fallback: treat as always day or night by noon altitude proxy
        sunrise = _utc_from_minutes(local_day, noon_min - 6 * 60).astimezone(tz)
        sunset = _utc_from_minutes(local_day, noon_min + 6 * 60).astimezone(tz)
    else:
        sunrise = _utc_from_minutes(local_day, noon_min - 4 * ha_rise).astimezone(tz)
        sunset = _utc_from_minutes(local_day, noon_min + 4 * ha_rise).astimezone(tz)

    if ha_civil is None:
        civil_dawn = sunrise - timedelta(minutes=30)
        civil_dusk = sunset + timedelta(minutes=30)
    else:
        civil_dawn = _utc_from_minutes(local_day, noon_min - 4 * ha_civil).astimezone(tz)
        civil_dusk = _utc_from_minutes(local_day, noon_min + 4 * ha_civil).astimezone(tz)

    golden_morning_end = sunrise + timedelta(hours=1)
    golden_evening_start = sunset - timedelta(hours=1)

    is_daylight = civil_dawn <= when <= civil_dusk

    if when < civil_dawn or when > civil_dusk:
        phase = "night"
    elif when < sunrise:
        phase = "civil_dawn"
    elif when < golden_morning_end:
        phase = "golden_morning"
    elif when < golden_evening_start:
        phase = "day"
    elif when < sunset:
        phase = "golden_evening"
    else:
        phase = "civil_dusk"

    return SunTimes(
        date_local=local_day.isoformat(),
        timezone=tz_name,
        sunrise=sunrise,
        sunset=sunset,
        civil_dawn=civil_dawn,
        civil_dusk=civil_dusk,
        golden_morning_end=golden_morning_end,
        golden_evening_start=golden_evening_start,
        is_daylight=is_daylight,
        phase=phase,
    )
