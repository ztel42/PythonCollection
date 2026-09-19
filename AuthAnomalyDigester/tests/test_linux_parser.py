"""Tests for Linux auth.log parser."""

from pathlib import Path

from auth_anomaly_digester.parsers.linux_auth import parse_linux_auth
from auth_anomaly_digester.parsers import detect_format, parse_file


def test_parse_ssh_failures_and_successes(auth_log: Path):
    text = auth_log.read_text(encoding="utf-8")
    events = parse_linux_auth(text)
    failures = [e for e in events if e.outcome == "failure" and e.event_type.startswith("ssh")]
    successes = [e for e in events if e.outcome == "success" and e.event_type.startswith("ssh")]
    assert len(failures) >= 11
    assert any(e.source_ip == "203.0.113.10" for e in failures)
    assert any(e.username == "alice" and e.source_ip == "198.51.100.20" for e in successes)
    assert any(e.event_type == "ssh_publickey" for e in successes)


def test_parse_sudo(auth_log: Path):
    text = auth_log.read_text(encoding="utf-8")
    events = parse_linux_auth(text)
    sudo = [e for e in events if e.event_type == "sudo"]
    assert any(e.outcome == "failure" and e.username == "alice" for e in sudo)
    assert any(e.outcome == "success" and e.username == "alice" for e in sudo)


def test_detect_format_linux(auth_log: Path):
    text = auth_log.read_text(encoding="utf-8")
    assert detect_format(text, auth_log) == "linux"


def test_parse_file_linux(auth_log: Path):
    events, fmt = parse_file(auth_log)
    assert fmt == "linux"
    assert len(events) > 0
