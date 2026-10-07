from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from preflight_go_no_go import fetch as fetch_mod
from preflight_go_no_go.fetch import fetch_kp, fetch_metars, load_metars_fixture


def test_load_fixture(fixtures_dir: Path):
    obs = load_metars_fixture(fixtures_dir / "metar_vfr.json")
    assert any(o.icao == "KXMR" for o in obs)


def test_fetch_metars_mocked(fixtures_dir: Path):
    payload = json.loads((fixtures_dir / "metar_vfr.json").read_text())

    def fake_get(url, timeout=20.0):
        assert "aviationweather.gov" in url
        assert "KXMR" in url
        return payload

    with patch.object(fetch_mod, "_get_json", side_effect=fake_get):
        obs = fetch_metars(["KXMR", "KCOF"])
    assert len(obs) == 3


def test_fetch_kp_mocked(fixtures_dir: Path):
    payload = json.loads((fixtures_dir / "kp_quiet.json").read_text())

    with patch.object(fetch_mod, "_get_json", return_value=payload):
        kp = fetch_kp()
    assert kp is not None
    assert kp.kp_index == 1
