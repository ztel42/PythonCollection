from entra_hygiene.checks.apps import analyze_app_hygiene
from tests.conftest import load_json


def test_app_hygiene_credentials_and_high_priv(as_of):
    data = load_json("applications.json")
    result = analyze_app_hygiene(
        applications=data["applications"],
        service_principals=data["servicePrincipals"],
        app_role_assignments=data["appRoleAssignments"],
        graph_app_roles=data["graphAppRoles"],
        expiry_days=30,
        as_of=as_of,
    )
    assert not result.skipped
    titles = [f.title for f in result.findings]
    assert any("Expired application password" in t for t in titles)
    assert any("password expiring within 30 days" in t for t in titles)
    assert any("certificate expiring within 30 days" in t for t in titles)
    assert any("high-privilege Graph application permission" in t for t in titles)

    perms = {f.extra.get("permission") for f in result.findings if f.extra.get("permission")}
    assert "Directory.ReadWrite.All" in perms
    assert "RoleManagement.ReadWrite.Directory" in perms
    assert "AppRoleAssignment.ReadWrite.All" in perms
    # User.Read.All alone should not be flagged as high-priv
    assert "User.Read.All" not in perms

    # Clean app should not appear in high-priv or expiry findings
    clean_findings = [f for f in result.findings if f.resource_name == "Clean Read-Only App"]
    assert clean_findings == []


def test_app_soft_skip():
    result = analyze_app_hygiene(
        applications=[],
        service_principals=[],
        soft_skip_reason="no Application.Read.All",
    )
    assert result.skipped
