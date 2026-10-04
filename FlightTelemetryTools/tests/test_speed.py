"""Haversine / speed estimation tests."""

from __future__ import annotations

from flight_telemetry.models import TelemetryFrame
from flight_telemetry.speed import estimate_speeds, haversine_m


def test_haversine_known_short_distance() -> None:
    # ~111.2 m per 0.001 deg latitude near equator
    d = haversine_m(0.0, 0.0, 0.001, 0.0)
    assert 110.0 < d < 112.5


def test_estimate_labels_source() -> None:
    frames = [
        TelemetryFrame(
            index=1,
            start_ms=0,
            end_ms=1000,
            latitude=0.0,
            longitude=0.0,
            altitude_m=10.0,
            altitude_source="absolute",
            speed_mps=None,
            speed_source="unknown",
        ),
        TelemetryFrame(
            index=2,
            start_ms=1000,
            end_ms=2000,
            latitude=0.001,
            longitude=0.0,
            altitude_m=10.0,
            altitude_source="absolute",
            speed_mps=None,
            speed_source="unknown",
        ),
    ]
    estimate_speeds(frames)
    assert frames[0].speed_source == "unknown"
    assert frames[1].speed_source == "estimated"
    assert frames[1].speed_mps is not None
    # ~111 m in 1 s
    assert 100.0 < frames[1].speed_mps < 120.0


def test_recorded_speed_not_overwritten() -> None:
    frames = [
        TelemetryFrame(
            index=1,
            start_ms=0,
            end_ms=1000,
            latitude=0.0,
            longitude=0.0,
            altitude_m=1.0,
            altitude_source="relative",
            speed_mps=2.0,
            speed_source="recorded",
        ),
        TelemetryFrame(
            index=2,
            start_ms=1000,
            end_ms=2000,
            latitude=0.001,
            longitude=0.0,
            altitude_m=1.0,
            altitude_source="relative",
            speed_mps=9.9,
            speed_source="recorded",
        ),
    ]
    estimate_speeds(frames)
    assert frames[1].speed_mps == 9.9
    assert frames[1].speed_source == "recorded"
