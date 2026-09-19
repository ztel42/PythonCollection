"""CLI and report tests."""

import json
from pathlib import Path

from auth_anomaly_digester.cli import main, run_digest
from auth_anomaly_digester.report import BANNER, write_csv, write_json


def test_run_digest_linux(auth_log: Path, baseline_ips: Path):
    report = run_digest(
        [auth_log],
        baseline=baseline_ips,
        bf_threshold=10,
        bf_window=10,
    )
    assert report.failure_count >= 11
    assert report.success_count >= 3
    assert any(f.detector == "brute_force" for f in report.findings)


def test_cli_json_csv(tmp_path: Path, auth_log: Path):
    json_path = tmp_path / "out.json"
    csv_path = tmp_path / "out.csv"
    rc = main(
        [
            str(auth_log),
            "--json",
            str(json_path),
            "--csv",
            str(csv_path),
            "--bf-threshold",
            "10",
        ]
    )
    assert rc == 0
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "findings" in data
    assert "READ-ONLY" in data["banner"]
    assert csv_path.is_file()
    assert "detector" in csv_path.read_text(encoding="utf-8").splitlines()[0]


def test_cli_windows(windows_csv: Path, capsys):
    rc = main([str(windows_csv), "--format", "windows"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "AUTHORIZED USE ONLY" in out or "READ-ONLY" in out
    assert "brute_force" in out or "Findings" in out


def test_cli_missing_file():
    rc = main(["/nonexistent/auth.log"])
    assert rc == 2


def test_banner_constant():
    assert "AUTHORIZED USE ONLY" in BANNER
    assert "READ-ONLY" in BANNER


def test_write_reports(tmp_path: Path, auth_log: Path):
    report = run_digest([auth_log])
    j = tmp_path / "r.json"
    c = tmp_path / "r.csv"
    write_json(report, str(j))
    write_csv(report, str(c))
    assert j.stat().st_size > 0
    assert c.stat().st_size > 0
