"""Parse real DJI .SRT telemetry dialects.

Supported layouts (documented public dialects):
- Classic / Format 3 (+3b): HTML <font>-wrapped lines with SrtCnt/FrameCnt,
  datetime, and bracket fields [latitude:] [longitude:] [rel_alt: abs_alt:].
- Bracket-style / Format 1: Mini/Air/Mavic key-value brackets (same GPS keys;
  may include [iso], gb_yaw, and optional speed tags when present).
- GPS function / Format 2 (+2b): GPS(lat,lon,alt[M]) / GPS (lat, lon, alt).
- Compact RTK / Format 2c: single-line with GPS (...) and H.S Nm/s.

Speed: prefer recorded horizontal speed (H.S, [h_spd], [speed]) when present;
otherwise estimate ground speed from successive GPS points (haversine).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from .models import TelemetryFrame
from .speed import estimate_speeds, haversine_m

PathLike = Union[str, Path]

# Cue timing: 00:00:00,000 --> 00:00:00,033  (comma or period milliseconds)
_TIME_RE = re.compile(
    r"(?P<sh>\d{1,2}):(?P<sm>\d{2}):(?P<ss>\d{2})[,.](?P<sms>\d{1,3})"
    r"\s*-->\s*"
    r"(?P<eh>\d{1,2}):(?P<em>\d{2}):(?P<es>\d{2})[,.](?P<ems>\d{1,3})"
)

_LAT_RE = re.compile(r"\[latitude\s*:\s*([+-]?\d+(?:\.\d+)?)\]", re.I)
_LON_RE = re.compile(r"\[longitude\s*:\s*([+-]?\d+(?:\.\d+)?)\]", re.I)
# rel_alt and abs_alt may share one bracket: [rel_alt: 1.300 abs_alt: 132.860]
_REL_ALT_RE = re.compile(r"rel_alt\s*:\s*([+-]?\d+(?:\.\d+)?)", re.I)
_ABS_ALT_RE = re.compile(r"abs_alt\s*:\s*([+-]?\d+(?:\.\d+)?)", re.I)

# Format 2 / 2b: GPS(lat,lon,alt) or GPS(lat,lon,altM)
_GPS_FUNC_RE = re.compile(
    r"GPS\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)[A-Za-z]*\s*\)",
    re.I,
)
# Format 2c: GPS (lat, lon, alt) with spaces after commas
_GPS_SPACE_RE = re.compile(
    r"GPS\s+\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*,\s*"
    r"([+-]?\d+(?:\.\d+)?)[A-Za-z]*\s*\)",
    re.I,
)

# Recorded horizontal speed variants
_HS_RE = re.compile(r"H\.S\s*([+-]?\d+(?:\.\d+)?)\s*m/s", re.I)
_H_SPD_RE = re.compile(r"\[h_spd\s*:\s*([+-]?\d+(?:\.\d+)?)\]", re.I)
_SPEED_BRACKET_RE = re.compile(r"\[speed\s*:\s*([+-]?\d+(?:\.\d+)?)\]", re.I)

# Datetime on its own line: 2024-01-15 14:30:22,123 or with .
_DT_RE = re.compile(
    r"(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})\s+"
    r"(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)

_HTML_TAG_RE = re.compile(r"</?font[^>]*>", re.I)


def _parse_ms(h: str, m: str, s: str, ms: str) -> int:
    ms_pad = (ms + "000")[:3]
    return (
        int(h) * 3_600_000
        + int(m) * 60_000
        + int(s) * 1_000
        + int(ms_pad)
    )


def _parse_datetime(text: str) -> Optional[datetime]:
    m = _DT_RE.search(text)
    if not m:
        return None
    ms = (m.group("ms") + "000")[:3]
    try:
        return datetime(
            int(m.group("y")),
            int(m.group("mo")),
            int(m.group("d")),
            int(m.group("h")),
            int(m.group("mi")),
            int(m.group("s")),
            int(ms) * 1000,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None


def _extract_speed(text: str) -> Optional[float]:
    for rx in (_HS_RE, _H_SPD_RE, _SPEED_BRACKET_RE):
        m = rx.search(text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _extract_gps(text: str) -> Optional[Tuple[float, float, Optional[float], Optional[float], Optional[float]]]:
    """Return (lat, lon, abs_alt, rel_alt, gps_alt_from_tuple) or None."""
    lat_m = _LAT_RE.search(text)
    lon_m = _LON_RE.search(text)
    if lat_m and lon_m:
        lat = float(lat_m.group(1))
        lon = float(lon_m.group(1))
        abs_m = _ABS_ALT_RE.search(text)
        rel_m = _REL_ALT_RE.search(text)
        abs_alt = float(abs_m.group(1)) if abs_m else None
        rel_alt = float(rel_m.group(1)) if rel_m else None
        return lat, lon, abs_alt, rel_alt, None

    for rx in (_GPS_FUNC_RE, _GPS_SPACE_RE):
        m = rx.search(text)
        if m:
            lat = float(m.group(1))
            lon = float(m.group(2))
            gps_alt = float(m.group(3))
            return lat, lon, None, None, gps_alt

    return None


def _split_cues(content: str) -> List[Tuple[int, int, int, str]]:
    """Split SRT into (index, start_ms, end_ms, body_text) tuples."""
    # Normalize newlines; strip BOM
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]

    blocks = re.split(r"\n\s*\n+", text.strip())
    cues: List[Tuple[int, int, int, str]] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != "" or True]
        # Keep structure: first non-empty may be index, then timing, then body
        nonempty = [ln for ln in block.split("\n")]
        if not any(ln.strip() for ln in nonempty):
            continue

        timing_idx = None
        start_ms = end_ms = 0
        index = len(cues) + 1
        for i, ln in enumerate(nonempty):
            tm = _TIME_RE.search(ln)
            if tm:
                timing_idx = i
                start_ms = _parse_ms(tm.group("sh"), tm.group("sm"), tm.group("ss"), tm.group("sms"))
                end_ms = _parse_ms(tm.group("eh"), tm.group("em"), tm.group("es"), tm.group("ems"))
                # Index line above timing if present
                if i > 0 and nonempty[i - 1].strip().isdigit():
                    index = int(nonempty[i - 1].strip())
                break
        if timing_idx is None:
            continue
        body_lines = nonempty[timing_idx + 1 :]
        body = "\n".join(body_lines)
        body = _HTML_TAG_RE.sub("", body)
        cues.append((index, start_ms, end_ms, body))
    return cues


def parse_srt_text(content: str) -> List[TelemetryFrame]:
    """Parse SRT text into frames that have lat/lon. Skip GPS-less cues."""
    frames: List[TelemetryFrame] = []
    for index, start_ms, end_ms, body in _split_cues(content):
        gps = _extract_gps(body)
        if gps is None:
            continue
        lat, lon, abs_alt, rel_alt, gps_alt = gps
        # Prefer absolute altitude when present, else relative, else GPS tuple alt
        if abs_alt is not None:
            altitude_m = abs_alt
            altitude_source = "absolute"
        elif rel_alt is not None:
            altitude_m = rel_alt
            altitude_source = "relative"
        elif gps_alt is not None:
            # Format 2 GPS() altitude is typically MSL / absolute-ish
            altitude_m = gps_alt
            altitude_source = "absolute"
            abs_alt = gps_alt
        else:
            altitude_m = 0.0
            altitude_source = "relative"

        recorded = _extract_speed(body)
        if recorded is not None:
            speed_mps = recorded
            speed_source = "recorded"
        else:
            speed_mps = None
            speed_source = "unknown"

        frames.append(
            TelemetryFrame(
                index=index,
                start_ms=start_ms,
                end_ms=end_ms,
                latitude=lat,
                longitude=lon,
                altitude_m=altitude_m,
                altitude_source=altitude_source,
                speed_mps=speed_mps,
                speed_source=speed_source,
                datetime_utc=_parse_datetime(body),
                rel_alt_m=rel_alt,
                abs_alt_m=abs_alt,
                raw_text=body,
            )
        )

    estimate_speeds(frames)
    return frames


def parse_srt_file(path: PathLike) -> List[TelemetryFrame]:
    """Read and parse a .SRT file (read-only)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"SRT file not found: {p}")
    # Try utf-8 then latin-1 for odd exports
    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_text(encoding="latin-1")
    return parse_srt_text(content)


# Re-export haversine for tests
__all__ = ["parse_srt_text", "parse_srt_file", "haversine_m"]
