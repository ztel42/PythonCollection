"""Parse NOAA SWPC planetary K-index JSON."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .models import KpReading


def parse_kp_json(payload: Union[List[Any], Dict[str, Any]]) -> Optional[KpReading]:
    """
    Parse https://services.swpc.noaa.gov/json/planetary_k_index_1m.json

    Each entry: {time_tag, kp_index, estimated_kp, kp}. Latest entry wins.
    Also tolerates products/noaa-planetary-k-index.json header+rows shape.
    """
    rows: List[Dict[str, Any]] = []
    if isinstance(payload, list):
        if not payload:
            return None
        # Header+rows style: first row is column names
        if (
            len(payload) >= 2
            and isinstance(payload[0], list)
            and all(isinstance(x, str) for x in payload[0])
        ):
            headers = [str(h) for h in payload[0]]
            for row in payload[1:]:
                if isinstance(row, list) and len(row) == len(headers):
                    rows.append(dict(zip(headers, row)))
        else:
            rows = [r for r in payload if isinstance(r, dict)]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        return None

    if not rows:
        return None

    last = rows[-1]
    kp_val = last.get("kp_index")
    if kp_val is None:
        kp_val = last.get("Kp") or last.get("kp")
    if kp_val is None:
        return None
    try:
        kp_f = float(kp_val)
    except (TypeError, ValueError):
        # e.g. "1P" style — strip non-numeric
        text = str(kp_val).strip()
        num = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if not num:
            return None
        kp_f = float(num)

    est = last.get("estimated_kp")
    est_f: Optional[float] = None
    if est is not None:
        try:
            est_f = float(est)
        except (TypeError, ValueError):
            est_f = None

    return KpReading(
        time_tag=str(last.get("time_tag") or last.get("time") or ""),
        kp_index=kp_f,
        estimated_kp=est_f,
    )
