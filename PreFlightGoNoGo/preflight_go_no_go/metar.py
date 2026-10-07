"""Parse aviationweather.gov METAR JSON into MetarObservation models."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .models import CloudLayer, MetarObservation


def _parse_visib(value: Any) -> Optional[float]:
    """Parse visibility: number, '10+', or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("+"):
        try:
            return float(text[:-1])
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_metar_json(item: Dict[str, Any]) -> MetarObservation:
    """Convert one aviationweather.gov /api/data/metar JSON object."""
    clouds_raw = item.get("clouds") or []
    clouds: List[CloudLayer] = []
    for c in clouds_raw:
        if not isinstance(c, dict):
            continue
        cover = str(c.get("cover") or "").upper()
        base = c.get("base")
        base_ft = int(base) if base is not None else None
        clouds.append(CloudLayer(cover=cover, base_ft=base_ft))

    return MetarObservation(
        icao=str(item.get("icaoId") or item.get("id") or "").upper(),
        name=str(item.get("name") or ""),
        raw=str(item.get("rawOb") or item.get("raw") or ""),
        report_time=item.get("reportTime") or item.get("obsTime"),
        lat=_float_or_none(item.get("lat")),
        lon=_float_or_none(item.get("lon")),
        temp_c=_float_or_none(item.get("temp")),
        dewp_c=_float_or_none(item.get("dewp")),
        wind_dir=_int_or_none(item.get("wdir")),
        wind_kt=_float_or_none(item.get("wspd")),
        gust_kt=_float_or_none(item.get("wgst")),
        vis_sm=_parse_visib(item.get("visib")),
        wx_string=item.get("wxString"),
        clouds=clouds,
        cover=item.get("cover"),
        flt_cat=item.get("fltCat"),
        altim_hpa=_float_or_none(item.get("altim")),
    )


def parse_metar_list(payload: Union[List[Any], Dict[str, Any]]) -> List[MetarObservation]:
    if isinstance(payload, dict):
        # unexpected wrapper
        for key in ("data", "metars", "features"):
            if key in payload and isinstance(payload[key], list):
                payload = payload[key]
                break
        else:
            return []
    out: List[MetarObservation] = []
    for item in payload:
        if isinstance(item, dict):
            # GeoJSON feature?
            props = item.get("properties") if "properties" in item else item
            if isinstance(props, dict):
                if "icaoId" not in props and "icaoId" in item:
                    props = item
                obs = parse_metar_json(props)
                if obs.icao:
                    out.append(obs)
    return out


def _float_or_none(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int_or_none(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
