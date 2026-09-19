"""Log parsers for Linux auth and Windows Security exports."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from ..models import AuthEvent
from .linux_auth import parse_linux_auth
from .windows_security import parse_windows_security


def detect_format(text: str, path: Optional[Path] = None) -> str:
    """Auto-detect log format from content and optional path hint."""
    name = (path.name if path else "").lower()
    sample = text[:4000].lower()

    if name.endswith(".csv") or ("," in sample and "event" in sample and "id" in sample):
        if "4624" in sample or "4625" in sample or "eventid" in sample.replace(" ", ""):
            return "windows"
    if name.endswith((".xml", ".evtx.txt", ".txt")) and (
        "4624" in sample or "4625" in sample or "<event" in sample
    ):
        return "windows"
    if "sshd" in sample or "sudo:" in sample or "failed password" in sample:
        return "linux"
    if "accepted password" in sample or "accepted publickey" in sample:
        return "linux"
    if "authentication failure" in sample:
        return "linux"
    # Path hints
    if "auth.log" in name or name == "secure" or "secure" in name:
        return "linux"
    if "security" in name and (name.endswith(".csv") or "export" in name):
        return "windows"
    return "linux"


def parse_file(
    path: Path,
    format_hint: Optional[str] = None,
) -> Tuple[List[AuthEvent], str]:
    """Parse a single log file; return events and format used."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fmt = format_hint or detect_format(text, path)
    if fmt in ("windows", "win", "csv", "xml"):
        events = parse_windows_security(text, source_path=str(path))
        return events, "windows"
    events = parse_linux_auth(text, source_path=str(path))
    return events, "linux"


def parse_files(
    paths: List[Path],
    format_hint: Optional[str] = None,
) -> Tuple[List[AuthEvent], str]:
    """Parse multiple files; format is majority / first detected."""
    all_events: List[AuthEvent] = []
    formats: List[str] = []
    for p in paths:
        events, fmt = parse_file(p, format_hint=format_hint)
        all_events.extend(events)
        formats.append(fmt)
    used = format_hint or (formats[0] if formats else "linux")
    if format_hint is None and formats:
        # Prefer windows if any file was windows when mixed? Use first.
        used = formats[0]
        if len(set(formats)) > 1:
            used = "mixed:" + ",".join(sorted(set(formats)))
    return all_events, used


__all__ = [
    "detect_format",
    "parse_file",
    "parse_files",
    "parse_linux_auth",
    "parse_windows_security",
]
