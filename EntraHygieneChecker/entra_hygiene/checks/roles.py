"""Privileged directory role membership checks."""

from __future__ import annotations

from typing import Any

from entra_hygiene.graph import GraphClient, GraphPermissionError
from entra_hygiene.models import CheckResult, Finding

# templateId -> friendly name for well-known high-risk directory roles
HIGH_RISK_ROLE_TEMPLATES: dict[str, str] = {
    "62e90394-69f5-4237-9190-012177145e10": "Global Administrator",
    "e8611ab8-c189-46e8-94e1-60213ab1f814": "Privileged Role Administrator",
    "9b895d92-2cd3-44c7-9d02-a6f93c84b91f": "Application Administrator",
    "cf1c38e5-3621-4004-a7cb-879624dced7c": "Cloud Application Administrator",
    "158c047a-c907-4556-b7ef-446551a6b5f7": "Cloud Device Administrator",
    "729827e3-9c14-49f7-bb1b-9608f156bbb8": "Helpdesk Administrator",
    "f28a1f50-f6e7-4571-818b-6a12f2af6b6c": "SharePoint Administrator",
    "29232a3b-7b54-4cbb-b7d0-3d0c2d4a0d0a": "Exchange Administrator",  # may vary; matched by displayName too
    "194ae4cb-b126-40b2-bd5b-6091b380977d": "Security Administrator",
    "fdd7a711-9b27-4799-97df-2dc934196713": "Directory Synchronization Accounts",
    "fe930be7-5e62-47db-91af-98c3a49a38b1": "User Administrator",
    "b0f54661-2d74-4c50-afa3-1ec803f12efe": "Billing Administrator",
    "3a2c62db-5318-420d-8d74-23affee5d9d5": "Intune Administrator",
    "4d6ac14f-3459-4b2b-a4d0-7e37001c6e0c": "Global Reader",  # lower risk but often reviewed
}

HIGH_RISK_DISPLAY_NAMES = {
    "Global Administrator",
    "Company Administrator",  # legacy display name
    "Privileged Role Administrator",
    "Application Administrator",
    "Cloud Application Administrator",
    "Security Administrator",
    "User Administrator",
    "Exchange Administrator",
    "SharePoint Administrator",
    "Helpdesk Administrator",
    "Conditional Access Administrator",
    "Privileged Authentication Administrator",
    "Authentication Administrator",
}


def analyze_privileged_roles(
    role_memberships: list[dict[str, Any]],
    *,
    soft_skip_reason: str | None = None,
) -> CheckResult:
    """
    Analyze privileged role memberships.

    Each item: {
      "roleTemplateId": "...",
      "displayName": "Global Administrator",
      "members": [{"id": "...", "userPrincipalName": "...", "displayName": "...", "@odata.type": "..."}]
    }
    """
    result = CheckResult(name="privileged_directory_roles")
    if soft_skip_reason:
        result.skipped = True
        result.skip_reason = soft_skip_reason
        return result

    result.notes.append(
        "High-risk roles reviewed: Global Administrator, Privileged Role Administrator, "
        "Application / Cloud Application Administrator, Security Administrator, "
        "User Administrator, and other well-known privileged directory roles."
    )

    for role in role_memberships:
        name = role.get("displayName") or ""
        template = role.get("roleTemplateId") or ""
        known = HIGH_RISK_ROLE_TEMPLATES.get(template)
        if not known and name not in HIGH_RISK_DISPLAY_NAMES:
            continue
        display = known or name
        members = role.get("members") or []
        upns = []
        for m in members:
            upn = m.get("userPrincipalName") or m.get("displayName") or m.get("id") or ""
            upns.append(str(upn))
        severity = "critical" if display in {"Global Administrator", "Company Administrator", "Privileged Role Administrator"} else "high"
        result.add(
            Finding(
                check="privileged_directory_roles",
                severity=severity,
                title=f"{display}: {len(members)} member(s)",
                detail=f"Members ({len(members)}): " + (", ".join(upns) if upns else "(none)"),
                resource_id=str(template or role.get("id") or ""),
                resource_name=str(display),
                extra={"member_count": len(members), "members": upns},
            )
        )
    return result


def collect_privileged_roles(client: GraphClient) -> CheckResult:
    """List activated directory roles and their members."""
    try:
        roles = client.get_all("directoryRoles", params={"$select": "id,displayName,roleTemplateId"})
    except GraphPermissionError as exc:
        return analyze_privileged_roles(
            [],
            soft_skip_reason=(
                f"Soft-skipped: Graph returned {exc.status} for directoryRoles. "
                "Grant Application permission RoleManagement.Read.Directory or Directory.Read.All."
            ),
        )

    memberships: list[dict[str, Any]] = []
    for role in roles:
        name = role.get("displayName") or ""
        template = role.get("roleTemplateId") or ""
        if template not in HIGH_RISK_ROLE_TEMPLATES and name not in HIGH_RISK_DISPLAY_NAMES:
            continue
        try:
            members = client.get_all(f"directoryRoles/{role['id']}/members")
        except GraphPermissionError as exc:
            return analyze_privileged_roles(
                [],
                soft_skip_reason=(
                    f"Soft-skipped: Graph returned {exc.status} reading role members. "
                    "Grant Application permission RoleManagement.Read.Directory or Directory.Read.All."
                ),
            )
        memberships.append(
            {
                "id": role.get("id"),
                "displayName": name,
                "roleTemplateId": template,
                "members": members,
            }
        )
    return analyze_privileged_roles(memberships)
