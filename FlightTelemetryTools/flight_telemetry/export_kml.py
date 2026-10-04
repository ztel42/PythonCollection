"""KML 2.2 LineString (+ gx:Track) export for Google Earth."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union
from xml.dom import minidom

from .models import TelemetryFrame

PathLike = Union[str, Path]

KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"


def _iso_time(frame: TelemetryFrame) -> str:
    if frame.datetime_utc is not None:
        return frame.datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    from datetime import datetime, timedelta, timezone

    t = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
        milliseconds=frame.start_ms
    )
    return t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _altitude_mode(frames: List[TelemetryFrame]) -> str:
    """Match altitudeMode to the dominant altitude source."""
    if not frames:
        return "absolute"
    abs_n = sum(1 for f in frames if f.altitude_source == "absolute")
    return "absolute" if abs_n >= len(frames) / 2 else "relativeToGround"


def frames_to_kml(frames: List[TelemetryFrame], name: str = "DJI flight track") -> str:
    """Build KML 2.2 with a LineString path and a gx:Track when times exist."""
    ET.register_namespace("", KML_NS)
    ET.register_namespace("gx", GX_NS)

    kml = ET.Element(f"{{{KML_NS}}}kml")
    doc = ET.SubElement(kml, f"{{{KML_NS}}}Document")
    ET.SubElement(doc, f"{{{KML_NS}}}name").text = name
    ET.SubElement(doc, f"{{{KML_NS}}}description").text = (
        "Flight track exported from DJI SRT telemetry for Google Earth. "
        "Coordinates and altitudes come from video subtitle metadata only; "
        "this is not a flight-controller log. Speed may be recorded or "
        "estimated from successive GPS points."
    )

    alt_mode = _altitude_mode(frames)

    # LineString placemark (always)
    pm = ET.SubElement(doc, f"{{{KML_NS}}}Placemark")
    ET.SubElement(pm, f"{{{KML_NS}}}name").text = f"{name} (path)"
    ET.SubElement(pm, f"{{{KML_NS}}}description").text = (
        f"{len(frames)} points; altitudeMode={alt_mode}"
    )
    line = ET.SubElement(pm, f"{{{KML_NS}}}LineString")
    ET.SubElement(line, f"{{{KML_NS}}}altitudeMode").text = alt_mode
    ET.SubElement(line, f"{{{KML_NS}}}tessellate").text = "1"
    coords = " ".join(
        f"{f.longitude:.7f},{f.latitude:.7f},{f.altitude_m:.3f}" for f in frames
    )
    ET.SubElement(line, f"{{{KML_NS}}}coordinates").text = coords

    # gx:Track with when/gx:coord
    track_pm = ET.SubElement(doc, f"{{{KML_NS}}}Placemark")
    ET.SubElement(track_pm, f"{{{KML_NS}}}name").text = f"{name} (track)"
    track = ET.SubElement(track_pm, f"{{{GX_NS}}}Track")
    ET.SubElement(track, f"{{{KML_NS}}}altitudeMode").text = alt_mode
    for fr in frames:
        ET.SubElement(track, f"{{{KML_NS}}}when").text = _iso_time(fr)
    for fr in frames:
        # gx:coord is lon lat alt (space-separated)
        ET.SubElement(track, f"{{{GX_NS}}}coord").text = (
            f"{fr.longitude:.7f} {fr.latitude:.7f} {fr.altitude_m:.3f}"
        )

    rough = ET.tostring(kml, encoding="utf-8")
    parsed = minidom.parseString(rough)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def write_kml(frames: List[TelemetryFrame], path: PathLike, name: str = "DJI flight track") -> Path:
    out = Path(path)
    out.write_text(frames_to_kml(frames, name=name), encoding="utf-8")
    return out
