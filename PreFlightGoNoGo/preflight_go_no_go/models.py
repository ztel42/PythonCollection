"""Shared data models and configurable scoring thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Verdict(str, Enum):
    FLY = "FLY"
    MARGINAL = "MARGINAL"
    DONT_FLY = "DON'T FLY"


# Severity order for combining factors
_SEVERITY = {Verdict.FLY: 0, Verdict.MARGINAL: 1, Verdict.DONT_FLY: 2}


def worse(a: Verdict, b: Verdict) -> Verdict:
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


@dataclass
class Thresholds:
    """Configurable go/no-go thresholds. Units: knots, statute miles, feet AGL, Kp index."""

    # Sustained wind (kt)
    wind_marginal_kt: float = 20.0
    wind_nofly_kt: float = 25.0
    # Gusts (kt)
    gust_marginal_kt: float = 25.0
    gust_nofly_kt: float = 30.0
    # Visibility (statute miles)
    vis_marginal_sm: float = 5.0
    vis_nofly_sm: float = 3.0
    # Ceiling BKN/OVC base (ft AGL)
    ceiling_marginal_ft: float = 1500.0
    ceiling_nofly_ft: float = 500.0
    # Planetary K-index (GPS scintillation / geomagnetic risk)
    kp_marginal: float = 5.0
    kp_nofly: float = 7.0
    # Night: civil twilight used as daylight boundary
    night_is_marginal: bool = True
    night_is_nofly: bool = False


@dataclass
class CloudLayer:
    cover: str  # FEW, SCT, BKN, OVC, VV, CLR, SKC
    base_ft: Optional[int] = None


@dataclass
class MetarObservation:
    icao: str
    name: str = ""
    raw: str = ""
    report_time: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    temp_c: Optional[float] = None
    dewp_c: Optional[float] = None
    wind_dir: Optional[int] = None
    wind_kt: Optional[float] = None
    gust_kt: Optional[float] = None
    vis_sm: Optional[float] = None  # None means unknown; float('inf') for 10+
    wx_string: Optional[str] = None
    clouds: List[CloudLayer] = field(default_factory=list)
    cover: Optional[str] = None
    flt_cat: Optional[str] = None
    altim_hpa: Optional[float] = None

    @property
    def ceiling_ft(self) -> Optional[int]:
        """Lowest BKN/OVC/VV base in feet AGL, if any."""
        bases = [
            c.base_ft
            for c in self.clouds
            if c.base_ft is not None and c.cover.upper() in {"BKN", "OVC", "VV"}
        ]
        return min(bases) if bases else None


@dataclass
class KpReading:
    time_tag: str
    kp_index: float
    estimated_kp: Optional[float] = None


@dataclass
class SunTimes:
    date_local: str
    timezone: str
    sunrise: datetime
    sunset: datetime
    civil_dawn: datetime
    civil_dusk: datetime
    golden_morning_end: datetime
    golden_evening_start: datetime
    is_daylight: bool  # civil dawn .. civil dusk
    phase: str  # night | civil_dawn | golden_morning | day | golden_evening | civil_dusk


@dataclass
class FactorResult:
    name: str
    verdict: Verdict
    detail: str


@dataclass
class StationRef:
    icao: str
    name: str
    lat: float
    lon: float
    distance_nm: Optional[float] = None


@dataclass
class GoNoGoReport:
    verdict: Verdict
    factors: List[FactorResult]
    primary_metar: Optional[MetarObservation]
    nearby_metars: List[MetarObservation]
    kp: Optional[KpReading]
    sun: Optional[SunTimes]
    location_label: str
    lat: Optional[float]
    lon: Optional[float]
    generated_at: datetime
    thresholds: Thresholds
