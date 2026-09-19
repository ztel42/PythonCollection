"""New source IP detection against a baseline or first-seen-in-file."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Set

from ..models import AuthEvent, Finding


def load_baseline_ips(path: Path) -> Set[str]:
    """Load known-good source IPs from a baseline file (one IP per line)."""
    ips: Set[str] = set()
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Allow "ip # comment" or csv first column
        token = line.split(",")[0].split()[0].strip()
        if token:
            ips.add(token)
    return ips


def detect_new_source_ips(
    events: List[AuthEvent],
    baseline: Optional[Set[str]] = None,
) -> List[Finding]:
    """Flag successful logons from IPs not in baseline / first-seen set.

    If ``baseline`` is provided, any success IP not in that set is new.
    If no baseline, the first success for each IP establishes baseline within
    the file; later first-seen IPs for *other* accounts still flag when the IP
    appears for the first time on a success (first occurrence of each IP is
    treated as establishing it — only report when IP was never seen before
    on any success, which means we report each distinct success IP once as
    "first seen in this file" when no baseline is given — useful for demos).

    Spec: "successful logon from an IP not seen in a prior baseline file
    (--baseline) or first-seen in this file if no baseline"

    Interpretation without baseline: each distinct success IP is reported
    once as first-seen-in-file (informational / low), since there is no prior
    history.
    """
    findings: List[Finding] = []

    if baseline is not None:
        seen_report: Set[str] = set()
        for ev in events:
            if ev.outcome != "success" or not ev.source_ip:
                continue
            if ev.source_ip in baseline:
                continue
            if ev.source_ip in seen_report:
                continue
            seen_report.add(ev.source_ip)
            findings.append(
                Finding(
                    detector="new_source_ip",
                    severity="medium",
                    summary=f"New source IP {ev.source_ip} (not in baseline)",
                    detail=(
                        f"Successful {ev.event_type} for "
                        f"{ev.username or '(unknown)'} from "
                        f"{ev.source_ip}, which is absent from the baseline."
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

    # No baseline: report each distinct success IP once as first-seen-in-file
    seen: Set[str] = set()
    for ev in events:
        if ev.outcome != "success" or not ev.source_ip:
            continue
        if ev.source_ip in seen:
            continue
        seen.add(ev.source_ip)
        findings.append(
            Finding(
                detector="new_source_ip",
                severity="low",
                summary=f"First-seen source IP {ev.source_ip} in this file",
                detail=(
                    f"No --baseline provided. First successful {ev.event_type} "
                    f"for {ev.username or '(unknown)'} from {ev.source_ip} "
                    f"in the analyzed file(s)."
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
