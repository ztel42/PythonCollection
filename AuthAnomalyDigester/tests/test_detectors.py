"""Tests for anomaly detectors."""

from datetime import datetime
from pathlib import Path

from auth_anomaly_digester.detectors import run_detectors
from auth_anomaly_digester.detectors.brute_force import detect_brute_force
from auth_anomaly_digester.detectors.new_source import (
    detect_new_source_ips,
    load_baseline_ips,
)
from auth_anomaly_digester.detectors.odd_hours import detect_odd_hours
from auth_anomaly_digester.models import AuthEvent
from auth_anomaly_digester.parsers import parse_file


def test_brute_force_from_auth_log(auth_log: Path):
    events, _ = parse_file(auth_log)
    findings = detect_brute_force(events, threshold=10, window_minutes=10)
    assert any(
        f.detector == "brute_force" and f.source_ip == "203.0.113.10" for f in findings
    )


def test_brute_force_from_windows_csv(windows_csv: Path):
    events, _ = parse_file(windows_csv, format_hint="windows")
    findings = detect_brute_force(events, threshold=10, window_minutes=10)
    assert any(f.source_ip == "203.0.113.50" for f in findings)


def test_odd_hours():
    events = [
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 2, 15, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="alice",
            source_ip="198.51.100.99",
        ),
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 10, 0, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="bob",
            source_ip="198.51.100.20",
        ),
    ]
    findings = detect_odd_hours(events, start_hour=7, end_hour=21)
    assert len(findings) == 1
    assert findings[0].username == "alice"


def test_new_source_with_baseline(baseline_ips: Path):
    events = [
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 10, 0, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="alice",
            source_ip="198.51.100.20",
        ),
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 10, 5, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="eve",
            source_ip="203.0.113.99",
        ),
    ]
    baseline = load_baseline_ips(baseline_ips)
    findings = detect_new_source_ips(events, baseline=baseline)
    assert len(findings) == 1
    assert findings[0].source_ip == "203.0.113.99"
    assert findings[0].severity == "medium"


def test_new_source_no_baseline_first_seen():
    events = [
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 10, 0, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="alice",
            source_ip="198.51.100.20",
        ),
        AuthEvent(
            timestamp=datetime(2026, 9, 18, 11, 0, 0),
            outcome="success",
            source="linux_auth",
            event_type="ssh_password",
            username="alice",
            source_ip="198.51.100.20",
        ),
    ]
    findings = detect_new_source_ips(events, baseline=None)
    assert len(findings) == 1
    assert findings[0].severity == "low"


def test_run_detectors_integration(auth_log: Path, baseline_ips: Path):
    events, _ = parse_file(auth_log)
    findings = run_detectors(
        events,
        bf_threshold=10,
        bf_window_minutes=10,
        odd_start_hour=7,
        odd_end_hour=21,
        baseline_path=baseline_ips,
    )
    dets = {f.detector for f in findings}
    assert "brute_force" in dets
    assert "odd_hours" in dets
    assert "new_source_ip" in dets
