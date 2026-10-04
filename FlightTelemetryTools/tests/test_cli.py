"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from flight_telemetry.cli import main


def test_parse_cli_writes_gpx_kml(classic_srt: Path, tmp_path: Path) -> None:
    gpx = tmp_path / "t.gpx"
    kml = tmp_path / "t.kml"
    rc = main(["parse", str(classic_srt), "--gpx", str(gpx), "--kml", str(kml)])
    assert rc == 0
    assert gpx.is_file() and gpx.stat().st_size > 0
    assert kml.is_file() and kml.stat().st_size > 0


def test_parse_requires_output(classic_srt: Path) -> None:
    rc = main(["parse", str(classic_srt)])
    assert rc == 2


def test_parse_missing_file(tmp_path: Path) -> None:
    rc = main(["parse", str(tmp_path / "missing.SRT"), "--gpx", str(tmp_path / "x.gpx")])
    assert rc == 1


def test_parse_no_gps(tmp_path: Path) -> None:
    srt = tmp_path / "empty.SRT"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nno gps here\n",
        encoding="utf-8",
    )
    rc = main(["parse", str(srt), "--gpx", str(tmp_path / "x.gpx")])
    assert rc == 1
