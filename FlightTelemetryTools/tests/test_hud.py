"""HUD burn tests (skip if ffmpeg/ffprobe not on PATH)."""

from __future__ import annotations

from pathlib import Path

import pytest

from flight_telemetry.hud import (
    burn_hud,
    ensure_ffmpeg,
    ffmpeg_available,
    frames_to_ass,
    make_silent_test_video,
    probe_is_video,
)
from flight_telemetry.parser import parse_srt_file


@pytest.fixture(scope="module")
def ffmpeg_ready() -> bool:
    return ffmpeg_available()


def test_ensure_ffmpeg_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "flight_telemetry.hud.shutil.which", lambda _name: None
    )
    with pytest.raises(RuntimeError, match="Install it with your package manager"):
        ensure_ffmpeg()


def test_ass_generation(bracket_srt: Path) -> None:
    frames = parse_srt_file(bracket_srt)
    ass = frames_to_ass(frames)
    assert "[Script Info]" in ass
    assert "Dialogue:" in ass
    assert "alt:" in ass
    assert "spd:" in ass


def test_burn_hud_on_generated_video(
    bracket_srt: Path, tmp_path: Path, ffmpeg_ready: bool
) -> None:
    if not ffmpeg_ready:
        pytest.skip("ffmpeg/ffprobe not available on PATH")
    video = make_silent_test_video(tmp_path / "src.mp4", duration_s=4.0)
    frames = parse_srt_file(bracket_srt)
    out = tmp_path / "hud.mp4"
    burn_hud(video, frames, out)
    assert out.is_file() and out.stat().st_size > 0
    assert probe_is_video(out)
