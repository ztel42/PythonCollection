"""Brute-force detection: many failures from same IP or account in a window."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..models import AuthEvent, Finding


def _sliding_max(
    timestamps: List[datetime],
    window: timedelta,
    threshold: int,
) -> Optional[Tuple[datetime, datetime, int]]:
    """Return (first, last, count) for densest window meeting threshold."""
    if len(timestamps) < threshold:
        return None
    ts = sorted(timestamps)
    best: Optional[Tuple[datetime, datetime, int]] = None
    left = 0
    for right in range(len(ts)):
        while ts[right] - ts[left] > window:
            left += 1
        count = right - left + 1
        if count >= threshold:
            cand = (ts[left], ts[right], count)
            if best is None or cand[2] > best[2]:
                best = cand
    return best


def detect_brute_force(
    events: List[AuthEvent],
    threshold: int = 10,
    window_minutes: int = 10,
) -> List[Finding]:
    """Flag bunches of failures from the same source IP or account."""
    window = timedelta(minutes=window_minutes)
    by_ip: Dict[str, List[datetime]] = defaultdict(list)
    by_user: Dict[str, List[datetime]] = defaultdict(list)
    # Events without timestamps: use positional synthetic times so we can
    # still count clusters within the file order (1-minute spacing).
    synthetic_base = datetime(2026, 1, 1, 0, 0, 0)

    for i, ev in enumerate(events):
        if ev.outcome != "failure":
            continue
        ts = ev.timestamp if ev.timestamp is not None else synthetic_base + timedelta(
            minutes=i
        )
        if ev.source_ip:
            by_ip[ev.source_ip].append(ts)
        if ev.username:
            by_user[ev.username].append(ts)

    findings: List[Finding] = []
    seen_keys = set()

    for ip, stamps in by_ip.items():
        hit = _sliding_max(stamps, window, threshold)
        if not hit:
            continue
        first, last, count = hit
        key = ("ip", ip)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        findings.append(
            Finding(
                detector="brute_force",
                severity="high",
                summary=f"Brute-force pattern from IP {ip}: {count} failures",
                detail=(
                    f"{count} failed auth events from {ip} within "
                    f"{window_minutes} minutes "
                    f"(threshold={threshold})."
                ),
                count=count,
                source_ip=ip,
                first_seen=first,
                last_seen=last,
                related_events=count,
            )
        )

    for user, stamps in by_user.items():
        hit = _sliding_max(stamps, window, threshold)
        if not hit:
            continue
        first, last, count = hit
        key = ("user", user)
        if key in seen_keys:
            continue
        # Skip if this user-cluster is entirely explained by an IP we already flagged
        # with same count — still report account-centric view when useful
        seen_keys.add(key)
        findings.append(
            Finding(
                detector="brute_force",
                severity="high",
                summary=f"Brute-force pattern against account {user}: {count} failures",
                detail=(
                    f"{count} failed auth events for account '{user}' within "
                    f"{window_minutes} minutes "
                    f"(threshold={threshold})."
                ),
                count=count,
                username=user,
                first_seen=first,
                last_seen=last,
                related_events=count,
            )
        )

    return findings
