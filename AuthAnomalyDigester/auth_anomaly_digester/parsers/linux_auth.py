"""Parser for Linux auth.log / syslog-style SSH and sudo lines."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from ..models import AuthEvent

# Examples:
# Sep 18 03:12:01 host sshd[1234]: Failed password for root from 203.0.113.10 port 51234 ssh2
# Sep 18 03:12:05 host sshd[1235]: Failed password for invalid user admin from 203.0.113.10 port 51235 ssh2
# Sep 18 08:01:00 host sshd[2001]: Accepted password for alice from 198.51.100.20 port 40022 ssh2
# Sep 18 08:02:00 host sshd[2002]: Accepted publickey for bob from 198.51.100.21 port 40023 ssh2
# Sep 18 09:00:00 host sudo: pam_unix(sudo:auth): authentication failure; logname=alice uid=1000 euid=0 tty=/dev/pts/0 ruser=alice rhost= user=alice
# Sep 18 09:01:00 host sudo: alice : TTY=pts/0 ; PWD=/home/alice ; USER=root ; COMMAND=/bin/ls

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_TS_SYSLOG = re.compile(
    r"^(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})",
    re.IGNORECASE,
)

# Optional ISO-ish prefix some modern journals emit when exported
_TS_ISO = re.compile(
    r"^(?P<iso>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)

_SSH_FAIL = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+)\s+from\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SSH_ACCEPT = re.compile(
    r"Accepted (?P<method>password|publickey) for (?P<user>\S+)\s+from\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SUDO_FAIL = re.compile(
    r"sudo:.*authentication failure.*(?:ruser=(?P<ruser>\S*))?.*user=(?P<user>\S+)",
    re.IGNORECASE,
)
_SUDO_OK = re.compile(
    r"sudo:\s+(?P<user>\S+)\s+:\s+TTY=.*USER=(?P<target>\S+)\s*;\s*COMMAND=",
    re.IGNORECASE,
)
_AUTH_FAIL_GENERIC = re.compile(
    r"authentication failure.*(?:rhost=(?P<ip>\S*))?.*user=(?P<user>\S+)",
    re.IGNORECASE,
)


def _parse_timestamp(line: str, default_year: int = 2026) -> Optional[datetime]:
    m = _TS_ISO.match(line)
    if m:
        raw = m.group("iso").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    m = _TS_SYSLOG.match(line)
    if not m:
        return None
    mon = _MONTHS[m.group("mon").lower()]
    day = int(m.group("day"))
    h, mi, s = int(m.group("h")), int(m.group("m")), int(m.group("s"))
    try:
        return datetime(default_year, mon, day, h, mi, s)
    except ValueError:
        return None


def parse_linux_auth(
    text: str,
    source_path: str = "",
    default_year: int = 2026,
) -> List[AuthEvent]:
    """Parse auth.log / secure style text into AuthEvent list."""
    events: List[AuthEvent] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        ts = _parse_timestamp(line, default_year=default_year)
        lower = line.lower()

        m = _SSH_FAIL.search(line)
        if m:
            events.append(
                AuthEvent(
                    timestamp=ts,
                    outcome="failure",
                    source="linux_auth",
                    event_type="ssh_password",
                    username=m.group("user"),
                    source_ip=m.group("ip"),
                    raw=line.rstrip(),
                    extras={"path": source_path},
                )
            )
            continue

        m = _SSH_ACCEPT.search(line)
        if m:
            method = m.group("method").lower()
            events.append(
                AuthEvent(
                    timestamp=ts,
                    outcome="success",
                    source="linux_auth",
                    event_type=f"ssh_{method}",
                    username=m.group("user"),
                    source_ip=m.group("ip"),
                    raw=line.rstrip(),
                    extras={"path": source_path, "method": method},
                )
            )
            continue

        if "sudo:" in lower and "authentication failure" in lower:
            m = _SUDO_FAIL.search(line) or _AUTH_FAIL_GENERIC.search(line)
            user = ""
            if m:
                user = m.groupdict().get("user") or m.groupdict().get("ruser") or ""
            events.append(
                AuthEvent(
                    timestamp=ts,
                    outcome="failure",
                    source="linux_auth",
                    event_type="sudo",
                    username=user,
                    source_ip="",
                    raw=line.rstrip(),
                    extras={"path": source_path},
                )
            )
            continue

        m = _SUDO_OK.search(line)
        if m and "authentication failure" not in lower:
            events.append(
                AuthEvent(
                    timestamp=ts,
                    outcome="success",
                    source="linux_auth",
                    event_type="sudo",
                    username=m.group("user"),
                    source_ip="",
                    raw=line.rstrip(),
                    extras={
                        "path": source_path,
                        "target_user": m.group("target"),
                    },
                )
            )
            continue

        # Generic pam authentication failure (non-sudo)
        if "authentication failure" in lower and "sshd" in lower:
            m = _AUTH_FAIL_GENERIC.search(line)
            if m:
                events.append(
                    AuthEvent(
                        timestamp=ts,
                        outcome="failure",
                        source="linux_auth",
                        event_type="ssh_auth",
                        username=m.group("user") or "",
                        source_ip=(m.group("ip") or "").rstrip(),
                        raw=line.rstrip(),
                        extras={"path": source_path},
                    )
                )

    return events
