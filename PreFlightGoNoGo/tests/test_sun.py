from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from preflight_go_no_go.sun import compute_sun_times


def test_space_coast_daylight_october():
    tz = ZoneInfo("America/New_York")
    # Midday EDT on 2026-10-07 near Cape Canaveral
    when = datetime(2026, 10, 7, 13, 0, tzinfo=tz)
    sun = compute_sun_times(28.39, -80.60, when=when, tz_name="America/New_York")
    assert sun.is_daylight
    assert sun.phase in {"day", "golden_morning", "golden_evening"}
    assert sun.sunrise.hour < 8  # ~7:xx EDT in early October FL
    assert sun.sunset.hour >= 18
    assert sun.civil_dawn < sun.sunrise < sun.golden_morning_end
    assert sun.golden_evening_start < sun.sunset < sun.civil_dusk


def test_night_phase():
    tz = ZoneInfo("America/New_York")
    when = datetime(2026, 10, 7, 23, 30, tzinfo=tz)
    sun = compute_sun_times(28.39, -80.60, when=when)
    assert not sun.is_daylight
    assert sun.phase == "night"
