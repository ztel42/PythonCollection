"""GPX 1.1 track export."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union
from xml.dom import minidom

from .models import TelemetryFrame

PathLike = Union[str, Path]

GPX_NS = "http://www.topografix.com/GPX/1/1"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def _iso_time(frame: TelemetryFrame) -> str:
    if frame.datetime_utc is not None:
        return frame.datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    # Fall back to cue start as offset from epoch-less video time — use a
    # synthetic timeline anchored at 1970-01-01 so GPX always has <time>.
    from datetime import datetime, timedelta, timezone

    t = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
        milliseconds=frame.start_ms
    )
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def frames_to_gpx(frames: List[TelemetryFrame], name: str = "DJI flight track") -> str:
    """Build a GPX 1.1 document string with a single trk/trkseg."""
    ET.register_namespace("", GPX_NS)
    ET.register_namespace("xsi", XSI_NS)

    gpx = ET.Element(
        f"{{{GPX_NS}}}gpx",
        {
            "version": "1.1",
            "creator": "FlightTelemetryTools",
            f"{{{XSI_NS}}}schemaLocation": (
                f"{GPX_NS} http://www.topografix.com/GPX/1/1/gpx.xsd"
            ),
        },
    )
    metadata = ET.SubElement(gpx, f"{{{GPX_NS}}}metadata")
    ET.SubElement(metadata, f"{{{GPX_NS}}}name").text = name
    ET.SubElement(metadata, f"{{{GPX_NS}}}desc").text = (
        "Flight track exported from DJI SRT telemetry. "
        "GPS from subtitles only; not a flight controller log."
    )

    trk = ET.SubElement(gpx, f"{{{GPX_NS}}}trk")
    ET.SubElement(trk, f"{{{GPX_NS}}}name").text = name
    seg = ET.SubElement(trk, f"{{{GPX_NS}}}trkseg")

    for fr in frames:
        pt = ET.SubElement(
            seg,
            f"{{{GPX_NS}}}trkpt",
            {"lat": f"{fr.latitude:.7f}", "lon": f"{fr.longitude:.7f}"},
        )
        ET.SubElement(pt, f"{{{GPX_NS}}}ele").text = f"{fr.altitude_m:.3f}"
        ET.SubElement(pt, f"{{{GPX_NS}}}time").text = _iso_time(fr)

    rough = ET.tostring(gpx, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def write_gpx(frames: List[TelemetryFrame], path: PathLike, name: str = "DJI flight track") -> Path:
    out = Path(path)
    out.write_text(frames_to_gpx(frames, name=name), encoding="utf-8")
    return out
