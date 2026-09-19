"""Tests for Windows Security CSV/XML parsers."""

from pathlib import Path

from auth_anomaly_digester.parsers.windows_security import (
    parse_windows_csv,
    parse_windows_security,
    parse_windows_xml,
)
from auth_anomaly_digester.parsers import detect_format, parse_file


def test_parse_windows_csv_4624_4625(windows_csv: Path):
    text = windows_csv.read_text(encoding="utf-8")
    events = parse_windows_csv(text)
    fails = [e for e in events if e.outcome == "failure"]
    oks = [e for e in events if e.outcome == "success"]
    assert len(fails) == 11
    assert all(e.extras.get("event_id") == "4625" for e in fails)
    assert len(oks) == 3
    assert any(e.username == "alice" and e.source_ip == "198.51.100.20" for e in oks)


def test_parse_windows_xml(windows_xml: Path):
    text = windows_xml.read_text(encoding="utf-8")
    events = parse_windows_xml(text)
    assert any(e.outcome == "failure" and e.source_ip == "203.0.113.50" for e in events)
    assert any(e.outcome == "success" and e.username == "alice" for e in events)


def test_detect_format_windows(windows_csv: Path):
    text = windows_csv.read_text(encoding="utf-8")
    assert detect_format(text, windows_csv) == "windows"


def test_parse_file_windows(windows_csv: Path):
    events, fmt = parse_file(windows_csv)
    assert fmt == "windows"
    assert len(events) >= 14


def test_dispatch_security(windows_csv: Path, windows_xml: Path):
    assert len(parse_windows_security(windows_csv.read_text())) >= 14
    assert len(parse_windows_security(windows_xml.read_text())) >= 2
