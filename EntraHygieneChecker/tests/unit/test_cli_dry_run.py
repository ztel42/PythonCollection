import json
from pathlib import Path

from entra_hygiene.cli import main


def test_dry_run_writes_json_and_csv(tmp_path: Path, fixtures_dir: Path):
    json_path = tmp_path / "report.json"
    csv_path = tmp_path / "report.csv"
    code = main(
        [
            "--dry-run",
            "--fixtures",
            str(fixtures_dir),
            "--json",
            str(json_path),
            "--csv",
            str(csv_path),
            "--quiet",
        ]
    )
    # Fixture data includes high/critical findings → exit 1 is expected
    assert code == 1
    assert json_path.exists()
    assert csv_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["summary"]["total_findings"] > 0
    assert report["summary"]["checks_skipped"] == 0
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "mfa_registration" in csv_text
    assert "privileged_directory_roles" in csv_text


def test_dry_run_missing_fixtures(tmp_path: Path):
    code = main(["--dry-run", "--fixtures", str(tmp_path)])
    assert code == 2
