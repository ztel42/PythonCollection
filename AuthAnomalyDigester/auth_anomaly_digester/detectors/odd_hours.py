"""Odd-hours detection: successful logons outside a local-hour window."""

from __future__ import annotations

from typing import List

from ..models import AuthEvent, Finding


def _outside_window(hour: int, start: int, end: int) -> bool:
    """Return True if hour is outside [start, end) local hours.

    Supports normal windows (07–21) and overnight windows (e.g. 22–06)
    where start > end.
    """
    if start == end:
        return False  # entire day allowed
    if start < end:
        return not (start <= hour < end)
    # overnight: allowed if hour >= start OR hour < end
    return not (hour >= start or hour < end)


def detect_odd_hours(
    events: List[AuthEvent],
    start_hour: int = 7,
    end_hour: int = 21,
) -> List[Finding]:
    """Flag successful logons outside the configured hour window."""
    findings: List[Finding] = []
    for ev in events:
        if ev.outcome != "success":
            continue
        if ev.timestamp is None:
            continue
        # Skip sudo-only noise for odd hours? Spec says successful logons —
        # include SSH and Windows logon; include sudo as elevated success too.
        hour = ev.timestamp.hour
        if not _outside_window(hour, start_hour, end_hour):
            continue
        findings.append(
            Finding(
                detector="odd_hours",
                severity="medium",
                summary=(
                    f"Successful {ev.event_type} for {ev.username or '(unknown)'} "
                    f"at odd hour {hour:02d}:00"
                ),
                detail=(
                    f"Success outside configured window "
                    f"{start_hour:02d}:00–{end_hour:02d}:00 "
                    f"(local). source_ip={ev.source_ip or 'n/a'}"
                ),
                count=1,
                username=ev.username,
                source_ip=ev.source_ip,
                first_seen=ev.timestamp,
                last_seen=ev.timestamp,
                related_events=1,
            )
        )
    return findings
