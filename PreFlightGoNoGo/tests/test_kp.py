from __future__ import annotations

import json
from pathlib import Path

from preflight_go_no_go.kp import parse_kp_json


def test_kp_quiet_latest(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "kp_quiet.json").read_text())
    kp = parse_kp_json(data)
    assert kp is not None
    assert kp.kp_index == 1
    assert kp.estimated_kp == 1.33


def test_kp_storm(fixtures_dir: Path):
    data = json.loads((fixtures_dir / "kp_storm.json").read_text())
    kp = parse_kp_json(data)
    assert kp is not None
    assert kp.kp_index == 7


def test_kp_header_rows_style():
    payload = [
        ["time_tag", "Kp", "a_running_average"],
        ["2026-10-07 12:00:00", "3", "12"],
        ["2026-10-07 15:00:00", "5", "22"],
    ]
    kp = parse_kp_json(payload)
    assert kp is not None
    assert kp.kp_index == 5
