"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def classic_srt(fixtures_dir: Path) -> Path:
    return fixtures_dir / "classic_dji.SRT"


@pytest.fixture
def bracket_srt(fixtures_dir: Path) -> Path:
    return fixtures_dir / "bracket_mini.SRT"


@pytest.fixture
def gps_func_srt(fixtures_dir: Path) -> Path:
    return fixtures_dir / "gps_function.SRT"
