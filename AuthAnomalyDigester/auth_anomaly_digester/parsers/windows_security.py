"""Parser for exported Windows Security events (CSV / simple XML text).

Full binary .evtx is not parsed here — export to CSV or XML text first
(Event Viewer / wevtutil / Get-WinEvent). Supports Event IDs 4624 and 4625.
"""

from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

from ..models import AuthEvent

_EVENT_ID_RE = re.compile(r"\b(4624|4625)\b")
_IP_RE = re.compile(
    r"\b(?:(?:\d{1,3}\.){3}\d{1,3}|::1|localhost)\b",
    re.IGNORECASE,
)


def _parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip().strip('"')
    # Common export forms
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(value.replace("Z", ""), fmt.replace("Z", ""))
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _norm_key(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", k.lower())


def _row_get(row: Dict[str, str], *candidates: str) -> str:
    norm = {_norm_key(k): v for k, v in row.items() if k is not None}
    for c in candidates:
        v = norm.get(_norm_key(c))
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _is_csv(text: str) -> bool:
    first = ""
    for line in text.splitlines():
        if line.strip():
            first = line
            break
    if not first:
        return False
    lower = first.lower()
    return ("," in first or ";" in first) and (
        "event" in lower or "time" in lower or "id" in lower or "account" in lower
    )


def _is_xml(text: str) -> bool:
    s = text.lstrip()
    return s.startswith("<?xml") or s.startswith("<Events") or s.startswith("<Event")


def parse_windows_csv(text: str, source_path: str = "") -> List[AuthEvent]:
    """Parse CSV export of Windows Security log (4624/4625)."""
    sample = text.lstrip("\ufeff")
    # Detect delimiter
    first = next((ln for ln in sample.splitlines() if ln.strip()), "")
    delim = ";" if first.count(";") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(sample), delimiter=delim)
    events: List[AuthEvent] = []
    for row in reader:
        if not row:
            continue
        eid = _row_get(row, "EventID", "Event Id", "Id", "EventID")
        if not eid:
            # Sometimes EventID is nested in Level/etc — scan values
            joined = " ".join(str(v) for v in row.values() if v)
            m = _EVENT_ID_RE.search(joined)
            eid = m.group(1) if m else ""
        if eid not in ("4624", "4625"):
            continue
        outcome = "success" if eid == "4624" else "failure"
        ts = _parse_dt(
            _row_get(
                row,
                "TimeCreated",
                "Time Generated",
                "Date and Time",
                "Timestamp",
                "Time",
                "SystemTime",
            )
        )
        user = _row_get(
            row,
            "TargetUserName",
            "Account Name",
            "AccountName",
            "User",
            "Username",
            "SubjectUserName",
        )
        ip = _row_get(
            row,
            "IpAddress",
            "Source Network Address",
            "Source Address",
            "ClientAddress",
            "Workstation Name",
            "Ip Address",
        )
        if ip in ("-", "::1", "127.0.0.1", ""):
            # keep empty-ish as-is for local; still record
            pass
        events.append(
            AuthEvent(
                timestamp=ts,
                outcome=outcome,
                source="windows_security",
                event_type="logon",
                username=user,
                source_ip=ip if ip not in ("-",) else "",
                raw=str(dict(row)),
                extras={"path": source_path, "event_id": eid},
            )
        )
    return events


def parse_windows_xml(text: str, source_path: str = "") -> List[AuthEvent]:
    """Parse simple XML / EVTX-export text with Event elements."""
    events: List[AuthEvent] = []
    # Wrap fragments if needed
    body = text.strip()
    if not body.startswith("<?xml") and not body.startswith("<Events"):
        if "<Event" in body:
            body = f"<Events>{body}</Events>"
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        # Fall back to line-oriented extraction
        return _parse_windows_text_fallback(text, source_path)

    # Handle namespaces loosely
    for ev in root.iter():
        tag = ev.tag.split("}")[-1] if "}" in ev.tag else ev.tag
        if tag != "Event":
            continue
        eid = ""
        ts: Optional[datetime] = None
        user = ""
        ip = ""
        data: Dict[str, str] = {}
        for child in ev.iter():
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if ctag == "EventID" and child.text:
                eid = child.text.strip()
            elif ctag == "TimeCreated":
                sys_t = child.attrib.get("SystemTime") or ""
                ts = _parse_dt(sys_t)
            elif ctag == "Data":
                name = child.attrib.get("Name", "")
                if name and child.text is not None:
                    data[name] = child.text.strip()
        if eid not in ("4624", "4625"):
            continue
        user = data.get("TargetUserName") or data.get("SubjectUserName") or ""
        ip = data.get("IpAddress") or data.get("WorkstationName") or ""
        if ip == "-":
            ip = ""
        events.append(
            AuthEvent(
                timestamp=ts,
                outcome="success" if eid == "4624" else "failure",
                source="windows_security",
                event_type="logon",
                username=user,
                source_ip=ip,
                raw=ET.tostring(ev, encoding="unicode"),
                extras={"path": source_path, "event_id": eid},
            )
        )
    return events


def _parse_windows_text_fallback(text: str, source_path: str) -> List[AuthEvent]:
    """Loose text extraction when XML is malformed."""
    events: List[AuthEvent] = []
    blocks = re.split(r"(?=\bEvent\s*ID\s*[:=]?\s*462[45]\b)", text, flags=re.I)
    for block in blocks:
        m = _EVENT_ID_RE.search(block)
        if not m:
            continue
        eid = m.group(1)
        # Timestamp: look for ISO-ish
        ts = None
        tm = re.search(
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
            block,
        )
        if tm:
            ts = _parse_dt(tm.group(1))
        user_m = re.search(
            r"(?:Account Name|TargetUserName|AccountName)\s*[:=]\s*(\S+)",
            block,
            re.I,
        )
        ip_m = re.search(
            r"(?:Source Network Address|IpAddress|Source Address)\s*[:=]\s*(\S+)",
            block,
            re.I,
        )
        user = user_m.group(1) if user_m else ""
        ip = ip_m.group(1) if ip_m else ""
        if ip == "-":
            ip = ""
        events.append(
            AuthEvent(
                timestamp=ts,
                outcome="success" if eid == "4624" else "failure",
                source="windows_security",
                event_type="logon",
                username=user,
                source_ip=ip,
                raw=block[:500].strip(),
                extras={"path": source_path, "event_id": eid},
            )
        )
    return events


def parse_windows_security(text: str, source_path: str = "") -> List[AuthEvent]:
    """Dispatch to CSV or XML/text parser."""
    if _is_csv(text):
        return parse_windows_csv(text, source_path=source_path)
    if _is_xml(text) or "<Event" in text:
        return parse_windows_xml(text, source_path=source_path)
    # Prefer CSV attempt then fallback
    if "," in text and "\n" in text:
        ev = parse_windows_csv(text, source_path=source_path)
        if ev:
            return ev
    return _parse_windows_text_fallback(text, source_path)
