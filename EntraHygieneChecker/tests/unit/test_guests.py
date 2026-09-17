from entra_hygiene.checks.guests import analyze_guests
from tests.conftest import load_json


def test_guests_stale_and_disabled(as_of):
    guests = load_json("guests.json")["value"]
    result = analyze_guests(guests, stale_days=90, as_of=as_of)
    assert not result.skipped
    by_title = {}
    for f in result.findings:
        by_title.setdefault(f.title, []).append(f.resource_name)

    assert "Disabled Guest" in by_title["Disabled guest still present"]
    stale_key = "Stale guest (no sign-in beyond 90 days)"
    assert "Stale Guest" in by_title[stale_key]
    assert "Never Signed In Guest" in by_title[stale_key]
    # Fresh guest within 90 days of 2026-09-16 should not be stale
    assert "Fresh Guest" not in by_title.get(stale_key, [])


def test_guests_soft_skip():
    result = analyze_guests([], soft_skip_reason="no User.Read.All")
    assert result.skipped
