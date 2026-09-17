from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def as_of() -> datetime:
    """Fixed 'now' so stale/expiry assertions are stable across calendar dates."""
    return datetime(2026, 9, 16, 17, 0, 0, tzinfo=timezone.utc)


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
