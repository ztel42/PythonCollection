"""Shared data models for auth events and anomaly findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AuthEvent:
    """Normalized authentication event from any supported log format."""

    timestamp: Optional[datetime]
    outcome: str  # "success" | "failure" | "unknown"
    source: str  # "linux_auth" | "windows_security"
    event_type: str  # e.g. ssh_password, ssh_publickey, sudo, logon
    username: str = ""
    source_ip: str = ""
    raw: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.timestamp is not None:
            d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class Finding:
    """A single anomaly finding produced by a detector."""

    detector: str
    severity: str  # high | medium | low
    summary: str
    detail: str = ""
    count: int = 1
    username: str = ""
    source_ip: str = ""
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    related_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.first_seen is not None:
            d["first_seen"] = self.first_seen.isoformat()
        if self.last_seen is not None:
            d["last_seen"] = self.last_seen.isoformat()
        return d


@dataclass
class DigestReport:
    """Full digester run report."""

    events: List[AuthEvent]
    findings: List[Finding]
    input_files: List[str]
    format_used: str
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.events if e.outcome == "success")

    @property
    def failure_count(self) -> int:
        return sum(1 for e in self.events if e.outcome == "failure")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "banner": (
                "READ-ONLY analysis of files you provide. "
                "Authorized use only. No live network attacks."
            ),
            "input_files": self.input_files,
            "format_used": self.format_used,
            "config": self.config,
            "event_count": len(self.events),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "events": [e.to_dict() for e in self.events],
        }
