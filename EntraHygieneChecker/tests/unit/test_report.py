from entra_hygiene.models import CheckResult, Finding
from entra_hygiene.report import build_report, flatten_findings


def test_build_report_counts():
    results = [
        CheckResult(
            name="a",
            findings=[
                Finding("a", "high", "t1", "d1"),
                Finding("a", "critical", "t2", "d2"),
            ],
        ),
        CheckResult(name="b", skipped=True, skip_reason="perm"),
    ]
    report = build_report(results, mode="dry-run", stale_days=90, expiry_days=30)
    assert report["summary"]["total_findings"] == 2
    assert report["summary"]["checks_skipped"] == 1
    assert report["summary"]["by_severity"]["critical"] == 1
    assert flatten_findings(results)[0].severity == "critical"
