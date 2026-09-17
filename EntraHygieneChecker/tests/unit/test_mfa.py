from entra_hygiene.checks.mfa import analyze_mfa
from tests.conftest import load_json


def test_mfa_flags_unregistered_members_and_guests():
    data = load_json("mfa_registration.json")["value"]
    result = analyze_mfa(data)
    assert not result.skipped
    titles = {(f.resource_name, f.title, f.severity) for f in result.findings}
    assert ("bob@contoso.com", "User without MFA registered", "high") in titles
    assert (
        "guest.user_fabrikam.com#EXT#@contoso.com",
        "User without MFA registered",
        "medium",
    ) in titles
    assert any(f.title.startswith("User MFA registered but not MFA-capable") for f in result.findings)
    # Alice fully registered — no finding
    assert not any(f.resource_name == "alice@contoso.com" for f in result.findings)


def test_mfa_soft_skip():
    result = analyze_mfa(None, soft_skip_reason="missing Reports.Read.All")
    assert result.skipped
    assert "Reports.Read.All" in result.skip_reason
    assert result.findings == []
