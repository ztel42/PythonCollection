"""CLI entry for Auth Anomaly Digester."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .detectors import run_detectors
from .models import DigestReport
from .parsers import parse_files
from .report import print_banner, print_summary, write_csv, write_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auth_anomaly_digester",
        description=(
            "Read-only CLI that parses authentication logs and flags likely "
            "anomalies (brute force, odd hours, new source IPs). "
            "Authorized log files only."
        ),
    )
    p.add_argument(
        "paths",
        nargs="+",
        metavar="LOG",
        help="Path(s) to auth log / Windows Security export files",
    )
    p.add_argument(
        "--format",
        choices=("auto", "linux", "windows"),
        default="auto",
        help="Input format (default: auto-detect)",
    )
    p.add_argument(
        "--json",
        metavar="PATH",
        help="Write full JSON report to PATH",
    )
    p.add_argument(
        "--csv",
        metavar="PATH",
        help="Write findings CSV report to PATH",
    )
    p.add_argument(
        "--baseline",
        metavar="PATH",
        help="Baseline file of known-good source IPs (one per line)",
    )
    p.add_argument(
        "--bf-threshold",
        type=int,
        default=10,
        metavar="N",
        help="Brute-force failure count threshold (default: 10)",
    )
    p.add_argument(
        "--bf-window",
        type=int,
        default=10,
        metavar="MINUTES",
        help="Brute-force time window in minutes (default: 10)",
    )
    p.add_argument(
        "--odd-start",
        type=int,
        default=7,
        metavar="HOUR",
        help="Start of normal local hours [0-23] (default: 7)",
    )
    p.add_argument(
        "--odd-end",
        type=int,
        default=21,
        metavar="HOUR",
        help="End of normal local hours [0-23], exclusive (default: 21)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def run_digest(
    paths: List[Path],
    *,
    format_hint: Optional[str] = None,
    baseline: Optional[Path] = None,
    bf_threshold: int = 10,
    bf_window: int = 10,
    odd_start: int = 7,
    odd_end: int = 21,
) -> DigestReport:
    hint = None if format_hint in (None, "auto") else format_hint
    events, fmt = parse_files(paths, format_hint=hint)
    findings = run_detectors(
        events,
        bf_threshold=bf_threshold,
        bf_window_minutes=bf_window,
        odd_start_hour=odd_start,
        odd_end_hour=odd_end,
        baseline_path=baseline,
    )
    return DigestReport(
        events=events,
        findings=findings,
        input_files=[str(p) for p in paths],
        format_used=fmt,
        config={
            "bf_threshold": bf_threshold,
            "bf_window_minutes": bf_window,
            "odd_start_hour": odd_start,
            "odd_end_hour": odd_end,
            "baseline": str(baseline) if baseline else None,
            "format_hint": format_hint or "auto",
        },
    )


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    print_banner(sys.stdout)

    paths = [Path(p) for p in args.paths]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        for p in missing:
            print(f"ERROR: file not found: {p}", file=sys.stderr)
        return 2

    baseline = Path(args.baseline) if args.baseline else None
    if baseline is not None and not baseline.is_file():
        print(f"ERROR: baseline not found: {baseline}", file=sys.stderr)
        return 2

    if not (0 <= args.odd_start <= 23 and 0 <= args.odd_end <= 23):
        print("ERROR: --odd-start/--odd-end must be in 0..23", file=sys.stderr)
        return 2

    report = run_digest(
        paths,
        format_hint=args.format,
        baseline=baseline,
        bf_threshold=args.bf_threshold,
        bf_window=args.bf_window,
        odd_start=args.odd_start,
        odd_end=args.odd_end,
    )
    print_summary(report, sys.stdout)

    if args.json:
        write_json(report, args.json)
        print(f"JSON report written: {args.json}")
    if args.csv:
        write_csv(report, args.csv)
        print(f"CSV report written: {args.csv}")

    return 0
