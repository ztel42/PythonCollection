from __future__ import annotations

import json
from pathlib import Path

from preflight_go_no_go.metar import parse_metar_json, parse_metar_list


def test_parse_vfr_fixture(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "metar_vfr.json").read_text())
    obs = parse_metar_list(data)
    assert len(obs) == 3
    kxmr = next(o for o in obs if o.icao == "KXMR")
    assert kxmr.wind_kt == 8
    assert kxmr.vis_sm == 10
    assert kxmr.ceiling_ft is None  # FEW is not a ceiling
    assert kxmr.flt_cat == "VFR"


def test_parse_mvfr_ceiling_and_wx(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "metar_mvfr.json").read_text())
    obs = parse_metar_list(data)
    kxmr = next(o for o in obs if o.icao == "KXMR")
    assert kxmr.ceiling_ft == 1600
    assert kxmr.wx_string == "-RA"
    assert kxmr.vis_sm == 7


def test_parse_visib_numeric_and_plus():
    a = parse_metar_json({"icaoId": "KAAA", "visib": "10+"})
    b = parse_metar_json({"icaoId": "KBBB", "visib": 3})
    assert a.vis_sm == 10
    assert b.vis_sm == 3


def test_thunderstorm_ceiling(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "metar_thunderstorm.json").read_text())
    obs = parse_metar_list(data)[0]
    assert obs.ceiling_ft == 800
    assert obs.gust_kt == 34
