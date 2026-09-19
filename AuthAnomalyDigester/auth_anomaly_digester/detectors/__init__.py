"""Anomaly detectors for auth events."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from ..models import AuthEvent, Finding
from .brute_force import detect_brute_force
from .new_source import detect_new_source_ips, load_baseline_ips
from .odd_hours import detect_odd_hours


def run_detectors(
    events: List[AuthEvent],
    *,
    bf_threshold: int = 10,
    bf_window_minutes: int = 10,
    odd_start_hour: int = 7,
    odd_end_hour: int = 21,
    baseline_path: Optional[Path] = None,
) -> List[Finding]:
    """Run all detectors and return combined findings."""
    findings: List[Finding] = []
    findings.extend(
        detect_brute_force(
            events,
            threshold=bf_threshold,
            window_minutes=bf_window_minutes,
        )
    )
    findings.extend(
        detect_odd_hours(
            events,
            start_hour=odd_start_hour,
            end_hour=odd_end_hour,
        )
    )
    baseline: Optional[Set[str]] = None
    if baseline_path is not None:
        baseline = load_baseline_ips(baseline_path)
    findings.extend(detect_new_source_ips(events, baseline=baseline))
    # Stable sort: severity then detector then summary
    sev_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(
        key=lambda f: (
            sev_order.get(f.severity, 9),
            f.detector,
            f.summary,
        )
    )
    return findings


__all__ = [
    "run_detectors",
    "detect_brute_force",
    "detect_odd_hours",
    "detect_new_source_ips",
    "load_baseline_ips",
]
