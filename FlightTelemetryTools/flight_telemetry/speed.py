"""Ground-speed helpers (haversine estimate when SRT has no recorded speed)."""

from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import TelemetryFrame

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c


def estimate_speeds(frames: List["TelemetryFrame"]) -> None:
    """Fill speed_mps for frames that lack a recorded horizontal speed.

    Uses successive GPS points and cue start times. Labels source as
    ``estimated``. Frames that already have ``recorded`` speed are left alone.
    The first frame without prior context keeps speed None / unknown unless
    it already has a recorded value.
    """
    prev = None
    for frame in frames:
        if frame.speed_source == "recorded" and frame.speed_mps is not None:
            prev = frame
            continue
        if prev is None:
            prev = frame
            continue
        dt_ms = frame.start_ms - prev.start_ms
        if dt_ms <= 0 and frame.datetime_utc and prev.datetime_utc:
            dt_ms = int(
                (frame.datetime_utc - prev.datetime_utc).total_seconds() * 1000
            )
        if dt_ms <= 0:
            prev = frame
            continue
        dist = haversine_m(
            prev.latitude, prev.longitude, frame.latitude, frame.longitude
        )
        frame.speed_mps = dist / (dt_ms / 1000.0)
        frame.speed_source = "estimated"
        prev = frame
