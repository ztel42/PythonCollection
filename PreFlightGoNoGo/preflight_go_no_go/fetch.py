"""HTTP fetchers for METAR and Kp (stdlib urllib). Offline fixtures via loaders."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, List, Optional, Sequence

from .kp import parse_kp_json
from .metar import parse_metar_list
from .models import KpReading, MetarObservation

METAR_URL = "https://aviationweather.gov/api/data/metar"
KP_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
USER_AGENT = "PreFlightGoNoGo/0.1 (+https://github.com/ztel42/PythonCollection)"


def _get_json(url: str, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def fetch_metars(icaos: Sequence[str], timeout: float = 20.0) -> List[MetarObservation]:
    ids = ",".join(i.strip().upper() for i in icaos if i.strip())
    if not ids:
        return []
    qs = urllib.parse.urlencode({"ids": ids, "format": "json", "hours": "2"})
    url = f"{METAR_URL}?{qs}"
    data = _get_json(url, timeout=timeout)
    return parse_metar_list(data)


def fetch_metars_bbox(
    lat: float,
    lon: float,
    *,
    delta_deg: float = 0.75,
    timeout: float = 20.0,
) -> List[MetarObservation]:
    """Fetch METARs in a small bbox around lat/lon (south,west,north,east)."""
    south, west = lat - delta_deg, lon - delta_deg
    north, east = lat + delta_deg, lon + delta_deg
    bbox = f"{south:.4f},{west:.4f},{north:.4f},{east:.4f}"
    qs = urllib.parse.urlencode({"bbox": bbox, "format": "json", "hours": "2"})
    url = f"{METAR_URL}?{qs}"
    data = _get_json(url, timeout=timeout)
    return parse_metar_list(data)


def fetch_kp(timeout: float = 20.0) -> Optional[KpReading]:
    data = _get_json(KP_URL, timeout=timeout)
    return parse_kp_json(data)


def load_metars_fixture(path: Path) -> List[MetarObservation]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_metar_list(data)


def load_kp_fixture(path: Path) -> Optional[KpReading]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return parse_kp_json(data)
