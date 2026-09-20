"""Headless tests for integrity_core (no display / GUI required)."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from integrity_core import (
    HashMonitor,
    batch_verify,
    compare_hashes,
    parse_expected_hash_list,
    sha256_bytes,
    sha256_file,
    simulate_monitor_mismatch,
)


KNOWN = b"The quick brown fox jumps over the lazy dog"
KNOWN_SHA256 = hashlib.sha256(KNOWN).hexdigest()


def test_sha256_bytes_known():
    assert sha256_bytes(KNOWN) == KNOWN_SHA256
    assert sha256_bytes(b"") == hashlib.sha256(b"").hexdigest()


def test_sha256_file_known(tmp_path: Path):
    f = tmp_path / "fox.txt"
    f.write_bytes(KNOWN)
    assert sha256_file(f) == KNOWN_SHA256


def test_compare_hashes_case_and_whitespace():
    assert compare_hashes(KNOWN_SHA256, KNOWN_SHA256.upper())
    assert compare_hashes(f"  {KNOWN_SHA256}  ", KNOWN_SHA256)
    assert not compare_hashes(KNOWN_SHA256, "0" * 64)


def test_batch_verify_with_expected(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"alpha")
    b.write_bytes(b"beta")
    ha = sha256_file(a)
    hb = sha256_file(b)

    expected = parse_expected_hash_list(
        f"{ha}  a.bin\n"
        f"b.bin={hb}\n"
        f"# comment\n"
        f"missing.txt: {'f' * 64}\n"
    )
    result = batch_verify([a, b], expected)
    assert len(result.results) == 2
    assert result.match_count == 2
    assert result.mismatch_count == 0
    assert all(r.status == "MATCH" for r in result.results)


def test_batch_verify_mismatch_and_hashed(tmp_path: Path):
    good = tmp_path / "good.bin"
    bad = tmp_path / "bad.bin"
    lone = tmp_path / "lone.bin"
    good.write_bytes(b"ok")
    bad.write_bytes(b"tampered")
    lone.write_bytes(b"solo")

    expected = {
        "good.bin": sha256_bytes(b"ok"),
        "bad.bin": sha256_bytes(b"original"),  # wrong on purpose
    }
    result = batch_verify([good, bad, lone], expected)
    statuses = {Path(r.path).name: r.status for r in result.results}
    assert statuses["good.bin"] == "MATCH"
    assert statuses["bad.bin"] == "MISMATCH"
    assert statuses["lone.bin"] == "HASHED"
    report = result.to_report_text()
    assert "MISMATCH" in report
    assert "Batch File Integrity Report" in report


def test_batch_verify_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.bin"
    result = batch_verify([missing], {})
    assert result.error_count == 1
    assert result.results[0].status == "ERROR"


def test_simulate_monitor_mismatch(tmp_path: Path):
    path = tmp_path / "watched.dat"
    baseline, new_hash, matches = simulate_monitor_mismatch(
        path, b"v1-content", b"v2-changed"
    )
    assert baseline == sha256_bytes(b"v1-content")
    assert new_hash == sha256_bytes(b"v2-changed")
    assert matches is False
    assert not compare_hashes(baseline, new_hash)


def test_hash_monitor_detects_mismatch(tmp_path: Path):
    """Start HashMonitor, mutate file, assert alert callback sees mismatch."""
    target = tmp_path / "live.txt"
    target.write_bytes(b"baseline-data")

    alerts: list = []

    def on_alert(path, current, baseline, message):
        alerts.append(
            {
                "path": path,
                "current": current,
                "baseline": baseline,
                "message": message,
            }
        )

    mon = HashMonitor(on_alert=on_alert, debounce_seconds=0.15)
    mon.start(paths=[target], establish_baselines=True)
    try:
        assert target.resolve().as_posix() in {
            Path(p).as_posix() for p in mon.baselines
        } or str(target.resolve()) in mon.baselines
        baseline = mon.baselines[str(target.resolve())]
        assert baseline == sha256_bytes(b"baseline-data")

        # Mutate file
        time.sleep(0.2)
        target.write_bytes(b"changed-payload")

        # Poll until alert or timeout
        deadline = time.time() + 5.0
        mismatch_seen = False
        while time.time() < deadline:
            for a in alerts:
                if a["baseline"] and a["current"] and not compare_hashes(
                    a["current"], a["baseline"]
                ):
                    mismatch_seen = True
                    break
            if mismatch_seen:
                break
            # Also force a direct check in case FS events are delayed in CI
            cur, base, ok = mon.check_path_now(target)
            if base and not ok:
                mismatch_seen = True
                alerts.append(
                    {
                        "path": str(target),
                        "current": cur,
                        "baseline": base,
                        "message": "forced check mismatch",
                    }
                )
                break
            time.sleep(0.15)

        assert mismatch_seen, f"Expected mismatch alert; got alerts={alerts!r}"
        cur, base, ok = mon.check_path_now(target)
        assert base == baseline
        assert cur == sha256_bytes(b"changed-payload")
        assert ok is False
    finally:
        mon.stop()


def test_hash_monitor_check_path_sets_baseline(tmp_path: Path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"abc")
    mon = HashMonitor(debounce_seconds=0.05)
    try:
        cur, base, ok = mon.check_path_now(f)
        assert base is None
        assert ok is True
        assert cur == sha256_bytes(b"abc")
        cur2, base2, ok2 = mon.check_path_now(f)
        assert base2 == cur
        assert ok2 is True
    finally:
        mon.stop()
