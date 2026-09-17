"""MFA / authentication method registration checks."""

from __future__ import annotations

from typing import Any

from entra_hygiene.graph import GraphClient, GraphPermissionError
from entra_hygiene.models import CheckResult, Finding


def analyze_mfa(registration_details: list[dict[str, Any]] | None, *, soft_skip_reason: str | None = None) -> CheckResult:
    """Analyze /reports/authenticationMethods/userRegistrationDetails-shaped data."""
    result = CheckResult(name="mfa_registration")
    if soft_skip_reason:
        result.skipped = True
        result.skip_reason = soft_skip_reason
        return result
    if registration_details is None:
        result.skipped = True
        result.skip_reason = "No MFA registration data provided"
        return result

    result.notes.append(
        "Based on Graph reports/authenticationMethods/userRegistrationDetails "
        "(isMfaRegistered / isMfaCapable). Per-user legacy MFA policy state is not "
        "fully exposed in v1.0; report fields are used where available."
    )

    for row in registration_details:
        upn = row.get("userPrincipalName") or row.get("userDisplayName") or ""
        uid = row.get("id") or row.get("userId") or ""
        user_type = row.get("userType") or ""
        is_mfa = bool(row.get("isMfaRegistered"))
        is_capable = row.get("isMfaCapable")
        methods = row.get("methodsRegistered") or []

        if not is_mfa:
            sev = "high" if (user_type or "").lower() != "guest" else "medium"
            result.add(
                Finding(
                    check="mfa_registration",
                    severity=sev,
                    title="User without MFA registered",
                    detail=(
                        f"isMfaRegistered=false; isMfaCapable={is_capable}; "
                        f"methodsRegistered={methods or '[]'}; userType={user_type or 'n/a'}"
                    ),
                    resource_id=str(uid),
                    resource_name=str(upn),
                    extra={"isMfaCapable": is_capable, "methodsRegistered": methods, "userType": user_type},
                )
            )
        elif is_capable is False:
            result.add(
                Finding(
                    check="mfa_registration",
                    severity="medium",
                    title="User MFA registered but not MFA-capable",
                    detail=f"isMfaRegistered=true but isMfaCapable=false; methods={methods}",
                    resource_id=str(uid),
                    resource_name=str(upn),
                    extra={"methodsRegistered": methods},
                )
            )
    return result


def collect_mfa(client: GraphClient) -> CheckResult:
    """Fetch MFA registration report from Graph (requires Reports.Read.All)."""
    try:
        rows = client.get_all(
            "reports/authenticationMethods/userRegistrationDetails",
            params={"$select": "id,userPrincipalName,userDisplayName,userType,isMfaRegistered,isMfaCapable,methodsRegistered"},
        )
    except GraphPermissionError as exc:
        return analyze_mfa(
            None,
            soft_skip_reason=(
                f"Soft-skipped: Graph returned {exc.status} for userRegistrationDetails. "
                "Grant Application permission Reports.Read.All (admin consent) to enable this check."
            ),
        )
    except Exception as exc:  # noqa: BLE001 — surface soft-skip for unexpected Graph shapes
        return analyze_mfa(None, soft_skip_reason=f"Soft-skipped MFA check: {exc}")
    return analyze_mfa(rows)
