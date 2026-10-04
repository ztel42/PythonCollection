"""Telemetry frame model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TelemetryFrame:
    """One GPS-bearing subtitle cue from a DJI .SRT file."""

    index: int
    start_ms: int
    end_ms: int
    latitude: float
    longitude: float
    altitude_m: float
    altitude_source: str  # "absolute" | "relative"
    speed_mps: Optional[float]
    speed_source: str  # "recorded" | "estimated" | "unknown"
    datetime_utc: Optional[datetime] = None
    rel_alt_m: Optional[float] = None
    abs_alt_m: Optional[float] = None
    raw_text: str = ""

    @property
    def cue_start_ass(self) -> str:
        """ASS timestamp (H:MM:SS.cs) for cue start."""
        return _ms_to_ass(self.start_ms)

    @property
    def cue_end_ass(self) -> str:
        return _ms_to_ass(self.end_ms)


def _ms_to_ass(ms: int) -> str:
    if ms < 0:
        ms = 0
    cs = (ms % 1000) // 10
    total_s = ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
