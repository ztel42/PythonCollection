"""Application / service principal hygiene checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from entra_hygiene.graph import GraphClient, GraphPermissionError
from entra_hygiene.models import CheckResult, Finding

# Well-known Microsoft Graph application (client) id
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"

# High-privilege Microsoft Graph application permission *values* (app roles).
HIGH_PRIVILEGE_GRAPH_ROLES: dict[str, str] = {
    "Directory.ReadWrite.All": "19dbc75e-c2e2-444c-a770-ec69d8559fc7",
    "RoleManagement.ReadWrite.Directory": "9e3f62cf-ca93-4989-b6ce-bf83c28f9fe8",
    "AppRoleAssignment.ReadWrite.All": "06b708a9-e830-4db3-a914-8e3965258c53",
    "Application.ReadWrite.All": "1bfefb4e-e292-4de0-8f4c-d997ad4b76be",
    "Application.ReadWrite.OwnedBy": "18a4783c-866b-4cc7-a460-3d5e5662c884",
    "User.ReadWrite.All": "741f803b-c850-494e-b5df-cde7c675a1ca",
    "Group.ReadWrite.All": "62a82d76-70ea-41e2-9197-370493514b87",
    "RoleManagement.ReadWrite.Exchange": "something-skip",  # not Graph SP; kept by value name match
    "Policy.ReadWrite.ConditionalAccess": "01c0a623-6290-4ba9-85f0-7764d1eacc84",
    "Directory.AccessAsUser.All": "placeholder-delegated-only",
}

HIGH_PRIVILEGE_VALUES = {k for k in HIGH_PRIVILEGE_GRAPH_ROLES if not k.startswith("RoleManagement.ReadWrite.Exchange")}
HIGH_PRIVILEGE_IDS = {
    v for k, v in HIGH_PRIVILEGE_GRAPH_ROLES.items() if v and "placeholder" not in v and "something" not in v
}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def analyze_app_hygiene(
    *,
    applications: list[dict[str, Any]],
    service_principals: list[dict[str, Any]],
    app_role_assignments: list[dict[str, Any]] | None = None,
    graph_app_roles: list[dict[str, Any]] | None = None,
    expiry_days: int = 30,
    as_of: datetime | None = None,
    soft_skip_reason: str | None = None,
) -> CheckResult:
    """Flag high-privilege app permissions and soon-expiring passwords/certs."""
    result = CheckResult(name="app_service_principal_hygiene")
    if soft_skip_reason:
        result.skipped = True
        result.skip_reason = soft_skip_reason
        return result

    now = as_of or datetime.now(timezone.utc)
    expiry_cutoff = now + timedelta(days=expiry_days)
    result.notes.append(
        f"Credential expiry window: {expiry_days} days (through {expiry_cutoff.date().isoformat()})."
    )
    result.notes.append(
        "High-privilege Graph application permissions flagged: "
        + ", ".join(sorted(v for v in HIGH_PRIVILEGE_VALUES if "Directory.AccessAsUser" not in v))
    )

    # Map Graph app role id -> value
    role_id_to_value: dict[str, str] = {}
    if graph_app_roles:
        for role in graph_app_roles:
            rid = role.get("id")
            val = role.get("value")
            if rid and val:
                role_id_to_value[str(rid)] = str(val)
    else:
        role_id_to_value = {v: k for k, v in HIGH_PRIVILEGE_GRAPH_ROLES.items() if v and "placeholder" not in v and "something" not in v}

    sp_by_id = {sp.get("id"): sp for sp in service_principals if sp.get("id")}
    app_by_id = {a.get("id"): a for a in applications if a.get("id")}
    app_by_appid = {a.get("appId"): a for a in applications if a.get("appId")}

    # --- Credential expiry on application objects ---
    for app in applications:
        name = app.get("displayName") or app.get("appId") or ""
        aid = app.get("id") or ""
        for cred_kind, key in (("password", "passwordCredentials"), ("certificate", "keyCredentials")):
            for cred in app.get(key) or []:
                end = _parse_dt(cred.get("endDateTime"))
                if end is None:
                    continue
                hint = cred.get("displayName") or cred.get("keyId") or ""
                if end < now:
                    result.add(
                        Finding(
                            check="app_service_principal_hygiene",
                            severity="high",
                            title=f"Expired application {cred_kind}",
                            detail=f"{cred_kind} expired {end.date().isoformat()}; key={hint}",
                            resource_id=str(aid),
                            resource_name=str(name),
                            extra={"appId": app.get("appId"), "credentialType": cred_kind, "endDateTime": cred.get("endDateTime")},
                        )
                    )
                elif end <= expiry_cutoff:
                    result.add(
                        Finding(
                            check="app_service_principal_hygiene",
                            severity="medium",
                            title=f"Application {cred_kind} expiring within {expiry_days} days",
                            detail=f"{cred_kind} expires {end.date().isoformat()}; key={hint}",
                            resource_id=str(aid),
                            resource_name=str(name),
                            extra={"appId": app.get("appId"), "credentialType": cred_kind, "endDateTime": cred.get("endDateTime")},
                        )
                    )

    # --- High privilege via requiredResourceAccess on application manifests ---
    for app in applications:
        name = app.get("displayName") or app.get("appId") or ""
        aid = app.get("id") or ""
        for rra in app.get("requiredResourceAccess") or []:
            if str(rra.get("resourceAppId")) != GRAPH_APP_ID:
                continue
            for access in rra.get("resourceAccess") or []:
                if str(access.get("type", "")).lower() != "role":
                    continue
                rid = str(access.get("id") or "")
                value = role_id_to_value.get(rid, rid)
                if rid in HIGH_PRIVILEGE_IDS or value in HIGH_PRIVILEGE_VALUES:
                    result.add(
                        Finding(
                            check="app_service_principal_hygiene",
                            severity="critical",
                            title="App requests high-privilege Graph application permission",
                            detail=f"requiredResourceAccess role {value} ({rid})",
                            resource_id=str(aid),
                            resource_name=str(name),
                            extra={"appId": app.get("appId"), "permission": value, "permissionId": rid},
                        )
                    )

    # --- High privilege via appRoleAssignments on service principals ---
    for assignment in app_role_assignments or []:
        role_id = str(assignment.get("appRoleId") or "")
        value = role_id_to_value.get(role_id, role_id)
        resource_id = assignment.get("resourceId")
        # Only care about assignments *to* Microsoft Graph SP (or unknown if fixture maps by role id)
        resource_sp = sp_by_id.get(resource_id) if resource_id else None
        resource_app_id = (resource_sp or {}).get("appId")
        if resource_app_id and resource_app_id != GRAPH_APP_ID:
            # Still flag if role id/value is in our high-priv set (fixtures may omit Graph SP)
            if role_id not in HIGH_PRIVILEGE_IDS and value not in HIGH_PRIVILEGE_VALUES:
                continue
        elif role_id not in HIGH_PRIVILEGE_IDS and value not in HIGH_PRIVILEGE_VALUES:
            continue

        principal_id = assignment.get("principalId")
        sp = sp_by_id.get(principal_id) or {}
        sp_name = sp.get("displayName") or assignment.get("principalDisplayName") or principal_id or ""
        app_obj = app_by_appid.get(sp.get("appId")) or app_by_id.get(principal_id) or {}
        result.add(
            Finding(
                check="app_service_principal_hygiene",
                severity="critical",
                title="Service principal granted high-privilege Graph application permission",
                detail=f"appRoleAssignment {value} ({role_id}) on principal {sp_name}",
                resource_id=str(principal_id or ""),
                resource_name=str(sp_name),
                extra={
                    "permission": value,
                    "permissionId": role_id,
                    "appId": sp.get("appId") or app_obj.get("appId"),
                    "assignmentId": assignment.get("id"),
                },
            )
        )

    return result


def collect_app_hygiene(client: GraphClient, *, expiry_days: int = 30) -> CheckResult:
    """Fetch apps, SPs, and Graph role assignments; soft-skip on missing Application.Read.All."""
    try:
        applications = client.get_all(
            "applications",
            params={
                "$select": "id,appId,displayName,passwordCredentials,keyCredentials,requiredResourceAccess",
            },
        )
        service_principals = client.get_all(
            "servicePrincipals",
            params={"$select": "id,appId,displayName,servicePrincipalType,accountEnabled"},
        )
    except GraphPermissionError as exc:
        return analyze_app_hygiene(
            applications=[],
            service_principals=[],
            soft_skip_reason=(
                f"Soft-skipped: Graph returned {exc.status} listing applications/servicePrincipals. "
                "Grant Application permission Application.Read.All (admin consent)."
            ),
        )

    graph_sp = next((sp for sp in service_principals if sp.get("appId") == GRAPH_APP_ID), None)
    graph_app_roles: list[dict[str, Any]] = []
    app_role_assignments: list[dict[str, Any]] = []

    if graph_sp and graph_sp.get("id"):
        try:
            # appRoles live on the Graph service principal
            detail = client.get(f"servicePrincipals/{graph_sp['id']}", params={"$select": "id,appId,appRoles"})
            graph_app_roles = detail.get("appRoles") or []
        except GraphPermissionError:
            graph_app_roles = []
        try:
            app_role_assignments = client.get_all(
                f"servicePrincipals/{graph_sp['id']}/appRoleAssignedTo",
            )
        except GraphPermissionError as exc:
            # Soft note but still analyze manifests
            result = analyze_app_hygiene(
                applications=applications,
                service_principals=service_principals,
                app_role_assignments=[],
                graph_app_roles=graph_app_roles,
                expiry_days=expiry_days,
            )
            result.notes.append(
                f"Could not list Graph appRoleAssignedTo ({exc.status}); "
                "high-priv detection falls back to application requiredResourceAccess only. "
                "Grant Application.Read.All / Directory.Read.All as needed."
            )
            return result

    return analyze_app_hygiene(
        applications=applications,
        service_principals=service_principals,
        app_role_assignments=app_role_assignments,
        graph_app_roles=graph_app_roles,
        expiry_days=expiry_days,
    )
