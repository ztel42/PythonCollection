"""Nearby METAR station helpers (haversine + curated Space Coast seed list)."""

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

from .models import MetarObservation, StationRef

# Seed stations useful for Florida Space Coast demos / offline nearest lookup.
SEED_STATIONS: List[StationRef] = [
    StationRef("KXMR", "Cape Kennedy AF Skid Strip, FL", 28.4674, -80.5589),
    StationRef("KTTS", "NASA Shuttle Landing Facility, FL", 28.5987, -80.6816),
    StationRef("KCOF", "Patrick SFB / Cocoa Beach, FL", 28.2420, -80.6080),
    StationRef("KTIX", "Space Coast Regional, Titusville, FL", 28.5148, -80.7992),
    StationRef("KMLB", "Melbourne Orlando Intl, FL", 28.1028, -80.6453),
    StationRef("KX21", "Arthur Dunn Airpark, Titusville, FL", 28.6226, -80.8355),
    StationRef("KDAB", "Daytona Beach Intl, FL", 29.1799, -81.0581),
    StationRef("KORL", "Orlando Executive, FL", 28.5455, -81.3329),
    StationRef("KMCO", "Orlando Intl, FL", 28.4294, -81.3089),
    StationRef("KSFB", "Orlando Sanford Intl, FL", 28.7776, -81.2375),
]


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_nm = 3440.065  # Earth radius in nautical miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r_nm * math.asin(math.sqrt(a))


def nearest_stations(
    lat: float,
    lon: float,
    n: int = 3,
    pool: Optional[Sequence[StationRef]] = None,
) -> List[StationRef]:
    stations = list(pool) if pool is not None else list(SEED_STATIONS)
    ranked: List[StationRef] = []
    for s in stations:
        d = haversine_nm(lat, lon, s.lat, s.lon)
        ranked.append(StationRef(s.icao, s.name, s.lat, s.lon, distance_nm=d))
    ranked.sort(key=lambda s: s.distance_nm if s.distance_nm is not None else 1e9)
    return ranked[: max(1, n)]


def pick_primary(
    observations: Sequence[MetarObservation],
    preferred_icao: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> Tuple[Optional[MetarObservation], List[MetarObservation]]:
    if not observations:
        return None, []
    by_icao = {o.icao.upper(): o for o in observations if o.icao}

    if preferred_icao and preferred_icao.upper() in by_icao:
        primary = by_icao[preferred_icao.upper()]
    elif lat is not None and lon is not None:
        def dist(o: MetarObservation) -> float:
            if o.lat is None or o.lon is None:
                return 1e9
            return haversine_nm(lat, lon, o.lat, o.lon)

        primary = min(observations, key=dist)
    else:
        primary = observations[0]

    nearby = [o for o in observations if o.icao != primary.icao]
    # Sort nearby by distance when possible
    if lat is not None and lon is not None:
        nearby.sort(
            key=lambda o: (
                haversine_nm(lat, lon, o.lat, o.lon)
                if o.lat is not None and o.lon is not None
                else 1e9
            )
        )
    return primary, nearby


def icao_list_from_latlon(lat: float, lon: float, n: int = 3) -> List[str]:
    return [s.icao for s in nearest_stations(lat, lon, n=n)]


def parse_stationinfo_json(payload: Iterable) -> List[StationRef]:
    out: List[StationRef] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        icao = str(item.get("icaoId") or item.get("id") or "").upper()
        if not icao:
            continue
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        out.append(
            StationRef(
                icao=icao,
                name=str(item.get("site") or item.get("name") or icao),
                lat=float(lat),
                lon=float(lon),
            )
        )
    return out
