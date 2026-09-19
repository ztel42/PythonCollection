"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def auth_log(fixtures_dir: Path) -> Path:
    return fixtures_dir / "auth.log"


@pytest.fixture
def windows_csv(fixtures_dir: Path) -> Path:
    return fixtures_dir / "windows_security.csv"


@pytest.fixture
def windows_xml(fixtures_dir: Path) -> Path:
    return fixtures_dir / "windows_security.xml"


@pytest.fixture
def baseline_ips(fixtures_dir: Path) -> Path:
    return fixtures_dir / "baseline_ips.txt"
