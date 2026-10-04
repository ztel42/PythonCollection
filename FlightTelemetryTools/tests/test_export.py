"""GPX / KML well-formed export tests."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from flight_telemetry.export_gpx import frames_to_gpx, write_gpx
from flight_telemetry.export_kml import frames_to_kml, write_kml
from flight_telemetry.parser import parse_srt_file


GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}
KML_NS = {
    "kml": "http://www.opengis.net/kml/2.2",
    "gx": "http://www.google.com/kml/ext/2.2",
}


def test_gpx_well_formed(classic_srt: Path, tmp_path: Path) -> None:
    frames = parse_srt_file(classic_srt)
    xml = frames_to_gpx(frames)
    root = ET.fromstring(xml)
    assert root.tag.endswith("gpx")
    pts = root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")
    assert len(pts) == len(frames)
    for pt in pts:
        assert "lat" in pt.attrib and "lon" in pt.attrib
        assert pt.find("{http://www.topografix.com/GPX/1/1}ele") is not None
        assert pt.find("{http://www.topografix.com/GPX/1/1}time") is not None
    out = write_gpx(frames, tmp_path / "out.gpx")
    assert out.is_file()
    ET.parse(out)


def test_kml_linestring_and_gx_track(classic_srt: Path, tmp_path: Path) -> None:
    frames = parse_srt_file(classic_srt)
    xml = frames_to_kml(frames)
    root = ET.fromstring(xml)
    assert root.tag.endswith("kml")
    coords = root.find(".//{http://www.opengis.net/kml/2.2}coordinates")
    assert coords is not None and coords.text and "," in coords.text
    whens = root.findall(".//{http://www.opengis.net/kml/2.2}when")
    gx_coords = root.findall(".//{http://www.google.com/kml/ext/2.2}coord")
    assert len(whens) == len(frames)
    assert len(gx_coords) == len(frames)
    alt_mode = root.find(".//{http://www.opengis.net/kml/2.2}altitudeMode")
    assert alt_mode is not None
    assert alt_mode.text in ("absolute", "relativeToGround")
    # classic fixture uses abs_alt -> absolute
    assert alt_mode.text == "absolute"
    out = write_kml(frames, tmp_path / "out.kml")
    ET.parse(out)
