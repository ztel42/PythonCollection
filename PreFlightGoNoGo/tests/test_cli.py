from __future__ import annotations

import json
from pathlib import Path

import pytest

from preflight_go_no_go.cli import main


def test_cli_fly_fixture(fixtures_dir: Path, capsys):
    code = main([
        "--icao", "KXMR",
        "--lat", "28.39",
        "--lon", "-80.60",
        "--fixture-metar", str(fixtures_dir / "metar_vfr.json"),
        "--fixture-kp", str(fixtures_dir / "kp_quiet.json"),
        "--now", "2026-10-07T13:00:00",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "FLY" in out
    assert "KXMR" in out
    assert "Sun" in out


def test_cli_dont_fly_exit_1(fixtures_dir: Path, capsys):
    code = main([
        "--icao", "KXMR",
        "--fixture-metar", str(fixtures_dir / "metar_thunderstorm.json"),
        "--fixture-kp", str(fixtures_dir / "kp_quiet.json"),
        "--lat", "28.39",
        "--lon", "-80.60",
        "--now", "2026-10-07T13:00:00",
    ])
    assert code == 1
    assert "DON'T FLY" in capsys.readouterr().out


def test_cli_json(fixtures_dir: Path, capsys):
    code = main([
        "--icao", "KXMR",
        "--lat", "28.39",
        "--lon", "-80.60",
        "--fixture-metar", str(fixtures_dir / "metar_vfr.json"),
        "--fixture-kp", str(fixtures_dir / "kp_quiet.json"),
        "--now", "2026-10-07T13:00:00",
        "--json",
    ])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "FLY"
    assert data["primary_metar"]["icao"] == "KXMR"
    assert "sunrise" in data["sun"]


def test_cli_missing_args_exits():
    with pytest.raises(SystemExit) as ei:
        main([])
    assert ei.value.code == 2
