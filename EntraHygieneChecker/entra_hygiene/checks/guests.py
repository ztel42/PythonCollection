"""Guest / external user hygiene checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from entra_hygiene.graph import GraphClient, GraphPermissionError
from entra_hygiene.models import CheckResult, Finding


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def analyze_guests(
    guests: list[dict[str, Any]],
    *,
    stale_days: int = 90,
    as_of: datetime | None = None,
    soft_skip_reason: str | None = None,
) -> CheckResult:
    """Flag stale guests (no recent sign-in) and disabled guests still present."""
    result = CheckResult(name="guest_users")
    if soft_skip_reason:
        result.skipped = True
        result.skip_reason = soft_skip_reason
        return result

    now = as_of or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=stale_days)
    result.notes.append(f"Stale threshold: no successful sign-in in {stale_days} days (cutoff {cutoff.date().isoformat()}).")
    result.notes.append("signInActivity requires AuditLog.Read.All and is often license-gated; missing activity is treated as never signed in.")

    for g in guests:
        upn = g.get("userPrincipalName") or ""
        uid = g.get("id") or ""
        display = g.get("displayName") or upn
        account_enabled = g.get("accountEnabled")
        created = g.get("createdDateTime")
        activity = g.get("signInActivity") or {}
        last_signin = (
            activity.get("lastSuccessfulSignInDateTime")
            or activity.get("lastSignInDateTime")
            or None
        )
        last_dt = _parse_dt(last_signin)

        if account_enabled is False:
            result.add(
                Finding(
                    check="guest_users",
                    severity="medium",
                    title="Disabled guest still present",
                    detail=f"accountEnabled=false; createdDateTime={created}; lastSignIn={last_signin or 'never'}",
                    resource_id=str(uid),
                    resource_name=str(display),
                    extra={"userPrincipalName": upn, "lastSignIn": last_signin},
                )
            )

        if account_enabled is not False:
            if last_dt is None or last_dt < cutoff:
                age_note = "never" if last_dt is None else last_dt.date().isoformat()
                result.add(
                    Finding(
                        check="guest_users",
                        severity="medium",
                        title=f"Stale guest (no sign-in beyond {stale_days} days)",
                        detail=f"lastSuccessful/lastSignIn={age_note}; createdDateTime={created}",
                        resource_id=str(uid),
                        resource_name=str(display),
                        extra={"userPrincipalName": upn, "lastSignIn": last_signin, "stale_days": stale_days},
                    )
                )
    return result


def collect_guests(client: GraphClient, *, stale_days: int = 90) -> CheckResult:
    """Fetch guest users; soft-skip if User.Read.All (or AuditLog for sign-in) missing."""
    select = (
        "id,displayName,userPrincipalName,accountEnabled,createdDateTime,"
        "userType,signInActivity,externalUserState"
    )
    try:
        guests = client.get_all(
            "users",
            params={
                "$filter": "userType eq 'Guest'",
                "$select": select,
                "$count": "true",
            },
        )
    except GraphPermissionError as exc:
        return analyze_guests(
            [],
            soft_skip_reason=(
                f"Soft-skipped: Graph returned {exc.status} listing guests. "
                "Grant Application permission User.Read.All (and AuditLog.Read.All for signInActivity)."
            ),
        )
    except Exception as exc:  # noqa: BLE001
        # Some tenants reject $select with signInActivity without AuditLog — retry without it.
        try:
            guests = client.get_all(
                "users",
                params={"$filter": "userType eq 'Guest'", "$select": "id,displayName,userPrincipalName,accountEnabled,createdDateTime,userType", "$count": "true"},
            )
            result = analyze_guests(guests, stale_days=stale_days)
            result.notes.append(
                f"signInActivity unavailable ({exc}); stale analysis treats missing last sign-in as never signed in."
            )
            return result
        except GraphPermissionError as exc2:
            return analyze_guests(
                [],
                soft_skip_reason=(
                    f"Soft-skipped: Graph returned {exc2.status} listing guests. "
                    "Grant Application permission User.Read.All."
                ),
            )
    return analyze_guests(guests, stale_days=stale_days)
