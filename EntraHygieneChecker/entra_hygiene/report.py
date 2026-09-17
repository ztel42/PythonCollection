"""Console / JSON / CSV report emitters."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from entra_hygiene.models import SEVERITY_ORDER, CheckResult, Finding


def flatten_findings(results: Iterable[CheckResult]) -> list[Finding]:
    findings: list[Finding] = []
    for r in results:
        findings.extend(r.findings)
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.check, f.resource_name))
    return findings


def build_report(
    results: list[CheckResult],
    *,
    mode: str,
    stale_days: int,
    expiry_days: int,
) -> dict[str, Any]:
    findings = flatten_findings(results)
    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    skipped = [r for r in results if r.skipped]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "parameters": {"stale_days": stale_days, "expiry_days": expiry_days},
        "summary": {
            "checks_run": len([r for r in results if not r.skipped]),
            "checks_skipped": len(skipped),
            "total_findings": len(findings),
            "by_severity": by_sev,
        },
        "skipped_checks": [{"name": r.name, "reason": r.skip_reason} for r in skipped],
        "checks": [r.to_dict() for r in results],
    }


def print_console(report: dict[str, Any], results: list[CheckResult]) -> None:
    summary = report["summary"]
    print("\n--- Summary ---")
    print(f"  Checks run:      {summary['checks_run']}")
    print(f"  Checks skipped:  {summary['checks_skipped']}")
    print(f"  Total findings:  {summary['total_findings']}")
    if summary["by_severity"]:
        parts = [f"{k}={v}" for k, v in sorted(summary["by_severity"].items(), key=lambda x: SEVERITY_ORDER.get(x[0], 99))]
        print(f"  By severity:     {', '.join(parts)}")

    for r in results:
        print(f"\n== {r.name} ==")
        if r.skipped:
            print(f"  SKIPPED: {r.skip_reason}")
            continue
        for note in r.notes:
            print(f"  note: {note}")
        if not r.findings:
            print("  (no findings)")
            continue
        for f in r.findings:
            label = f.resource_name or f.resource_id or "-"
            print(f"  [{f.severity.upper():8}] {f.title} — {label}")
            print(f"             {f.detail}")


def write_json(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(results: list[CheckResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    findings = flatten_findings(results)
    fieldnames = ["check", "severity", "title", "resource_name", "resource_id", "detail"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for f in findings:
            writer.writerow(
                {
                    "check": f.check,
                    "severity": f.severity,
                    "title": f.title,
                    "resource_name": f.resource_name,
                    "resource_id": f.resource_id,
                    "detail": f.detail,
                }
            )
