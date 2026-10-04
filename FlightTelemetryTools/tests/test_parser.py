"""Parser tests across DJI SRT dialects."""

from __future__ import annotations

from pathlib import Path

import pytest

from flight_telemetry.parser import parse_srt_file, parse_srt_text


def test_classic_font_wrapped(classic_srt: Path) -> None:
    frames = parse_srt_file(classic_srt)
    # 4 cues, 1 missing GPS -> 3 frames
    assert len(frames) == 3
    assert frames[0].latitude == pytest.approx(59.302335)
    assert frames[0].longitude == pytest.approx(18.203059)
    assert frames[0].altitude_source == "absolute"
    assert frames[0].altitude_m == pytest.approx(142.760)
    assert frames[0].abs_alt_m == pytest.approx(142.760)
    assert frames[0].rel_alt_m == pytest.approx(10.200)
    assert frames[0].datetime_utc is not None


def test_bracket_mini_and_missing_gps(bracket_srt: Path) -> None:
    frames = parse_srt_file(bracket_srt)
    # cues 1,2,4 have GPS; cue 3 missing
    assert len(frames) == 3
    assert frames[0].speed_source == "recorded"
    assert frames[0].speed_mps == pytest.approx(3.50)
    # frame 2 has no recorded speed -> estimated from previous
    assert frames[1].speed_source == "estimated"
    assert frames[1].speed_mps is not None and frames[1].speed_mps > 0


def test_gps_function_and_hs(gps_func_srt: Path) -> None:
    frames = parse_srt_file(gps_func_srt)
    assert len(frames) == 2
    assert frames[0].latitude == pytest.approx(39.906217)
    assert frames[0].altitude_m == pytest.approx(69.800)
    assert frames[0].altitude_source == "absolute"
    assert frames[1].speed_source == "recorded"
    assert frames[1].speed_mps == pytest.approx(4.25)


def test_skip_empty_and_no_file(tmp_path: Path) -> None:
    assert parse_srt_text("") == []
    missing = tmp_path / "nope.SRT"
    with pytest.raises(FileNotFoundError):
        parse_srt_file(missing)


def test_rel_alt_only_when_abs_missing() -> None:
    text = """1
00:00:00,000 --> 00:00:01,000
[latitude: 10.0] [longitude: 20.0] [rel_alt: 7.5]
"""
    frames = parse_srt_text(text)
    assert len(frames) == 1
    assert frames[0].altitude_source == "relative"
    assert frames[0].altitude_m == pytest.approx(7.5)
