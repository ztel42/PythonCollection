from __future__ import annotations

from preflight_go_no_go.stations import icao_list_from_latlon, nearest_stations, pick_primary
from preflight_go_no_go.metar import parse_metar_json


def test_nearest_space_coast():
    near = nearest_stations(28.39, -80.60, n=3)
    codes = [s.icao for s in near]
    assert "KXMR" in codes
    assert near[0].distance_nm is not None
    assert near[0].distance_nm < near[-1].distance_nm


def test_icao_list():
    codes = icao_list_from_latlon(28.39, -80.60, n=3)
    assert len(codes) == 3
    assert codes[0] == "KXMR"


def test_pick_primary_preferred():
    a = parse_metar_json({"icaoId": "KCOF", "lat": 28.24, "lon": -80.61, "wspd": 5})
    b = parse_metar_json({"icaoId": "KXMR", "lat": 28.47, "lon": -80.56, "wspd": 5})
    primary, nearby = pick_primary([a, b], preferred_icao="KXMR")
    assert primary is not None and primary.icao == "KXMR"
    assert len(nearby) == 1
