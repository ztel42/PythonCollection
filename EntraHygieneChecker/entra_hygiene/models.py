"""Shared finding / check-result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "skip": 5}


@dataclass
class Finding:
    check: str
    severity: str
    title: str
    detail: str
    resource_id: str = ""
    resource_name: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class CheckResult:
    name: str
    findings: list[Finding] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "notes": self.notes,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
        }
