from entra_hygiene.checks.roles import analyze_privileged_roles
from tests.conftest import load_json


def test_privileged_roles_lists_members():
    roles = load_json("directory_roles.json")["roles"]
    result = analyze_privileged_roles(roles)
    assert not result.skipped
    by_name = {f.resource_name: f for f in result.findings}
    assert "Global Administrator" in by_name
    assert by_name["Global Administrator"].extra["member_count"] == 2
    assert "alice@contoso.com" in by_name["Global Administrator"].extra["members"]
    assert "breakglass@contoso.com" in by_name["Global Administrator"].extra["members"]
    assert by_name["Global Administrator"].severity == "critical"
    assert "Privileged Role Administrator" in by_name
    assert "Application Administrator" in by_name
    # Reports Reader is not high-risk → omitted
    assert "Reports Reader" not in by_name


def test_roles_soft_skip():
    result = analyze_privileged_roles([], soft_skip_reason="no RoleManagement.Read.Directory")
    assert result.skipped
