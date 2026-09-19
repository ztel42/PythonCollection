"""Console, JSON, and CSV report writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TextIO

from .models import DigestReport

BANNER = """\
========================================================================
  READ-ONLY ANALYSIS OF FILES YOU PROVIDE  |  AUTHORIZED USE ONLY
  No live network attacks. No credential guessing. Portfolio / IR hygiene.
========================================================================"""


def print_banner(out: TextIO) -> None:
    out.write(BANNER + "\n")


def print_summary(report: DigestReport, out: TextIO) -> None:
    out.write("\nAuth Anomaly Digester — summary\n")
    out.write(f"  Format       : {report.format_used}\n")
    out.write(f"  Input files  : {len(report.input_files)}\n")
    for p in report.input_files:
        out.write(f"    - {p}\n")
    out.write(f"  Events       : {len(report.events)}\n")
    out.write(f"    - success  : {report.success_count}\n")
    out.write(f"    - failure  : {report.failure_count}\n")
    out.write(f"  Findings     : {len(report.findings)}\n")

    by_sev = {}
    by_det = {}
    for f in report.findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        by_det[f.detector] = by_det.get(f.detector, 0) + 1
    for sev in ("high", "medium", "low"):
        if sev in by_sev:
            out.write(f"    - {sev}: {by_sev[sev]}\n")
    if by_det:
        out.write("  By detector  :\n")
        for det, n in sorted(by_det.items()):
            out.write(f"    - {det}: {n}\n")

    if report.findings:
        out.write("\n  Top findings:\n")
        for f in report.findings[:20]:
            out.write(f"    [{f.severity}] {f.detector}: {f.summary}\n")
        if len(report.findings) > 20:
            out.write(f"    ... and {len(report.findings) - 20} more\n")
    else:
        out.write("\n  No anomalies flagged with current thresholds.\n")
    out.write("\n")


def write_json(report: DigestReport, path: str) -> None:
    Path(path).write_text(
        json.dumps(report.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(report: DigestReport, path: str) -> None:
    fieldnames = [
        "detector",
        "severity",
        "summary",
        "detail",
        "count",
        "username",
        "source_ip",
        "first_seen",
        "last_seen",
        "related_events",
    ]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for f in report.findings:
            row = f.to_dict()
            writer.writerow({k: row.get(k, "") for k in fieldnames})
