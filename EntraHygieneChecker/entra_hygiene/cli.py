"""CLI entrypoint for EntraHygieneChecker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from entra_hygiene import BANNER, __version__
from entra_hygiene.auth import acquire_token
from entra_hygiene.checks.apps import analyze_app_hygiene, collect_app_hygiene
from entra_hygiene.checks.guests import analyze_guests, collect_guests
from entra_hygiene.checks.mfa import analyze_mfa, collect_mfa
from entra_hygiene.checks.roles import analyze_privileged_roles, collect_privileged_roles
from entra_hygiene.graph import GraphClient
from entra_hygiene.models import CheckResult
from entra_hygiene.report import build_report, print_console, write_csv, write_json

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _load_fixture(fixtures_dir: Path, name: str):
    path = fixtures_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_dry(fixtures_dir: Path, stale_days: int, expiry_days: int) -> list[CheckResult]:
    mfa_data = _load_fixture(fixtures_dir, "mfa_registration.json")
    guests_data = _load_fixture(fixtures_dir, "guests.json")
    apps_data = _load_fixture(fixtures_dir, "applications.json")
    roles_data = _load_fixture(fixtures_dir, "directory_roles.json")

    results = [
        analyze_mfa(mfa_data.get("value") or mfa_data),
        analyze_guests(guests_data.get("value") or guests_data, stale_days=stale_days),
        analyze_app_hygiene(
            applications=apps_data.get("applications") or [],
            service_principals=apps_data.get("servicePrincipals") or [],
            app_role_assignments=apps_data.get("appRoleAssignments") or [],
            graph_app_roles=apps_data.get("graphAppRoles") or [],
            expiry_days=expiry_days,
        ),
        analyze_privileged_roles(roles_data.get("roles") or roles_data),
    ]
    return results


def run_live(stale_days: int, expiry_days: int) -> list[CheckResult]:
    token = acquire_token()
    client = GraphClient(token)
    return [
        collect_mfa(client),
        collect_guests(client, stale_days=stale_days),
        collect_app_hygiene(client, expiry_days=expiry_days),
        collect_privileged_roles(client),
    ]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="entra-hygiene",
        description="Read-only Microsoft Entra ID / Azure AD security hygiene checker.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load tests/fixtures JSON and run analyzers (no Azure / Graph calls).",
    )
    p.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Fixture directory for --dry-run (default: tests/fixtures).",
    )
    p.add_argument("--stale-days", type=int, default=90, help="Guest stale sign-in threshold (default 90).")
    p.add_argument("--expiry-days", type=int, default=30, help="App credential expiry window (default 30).")
    p.add_argument("--json", type=Path, metavar="PATH", help="Write full JSON report to PATH.")
    p.add_argument("--csv", type=Path, metavar="PATH", help="Write findings CSV to PATH.")
    p.add_argument("--quiet", action="store_true", help="Suppress console finding details (summary only).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(BANNER)

    mode = "dry-run" if args.dry_run else "live"
    try:
        if args.dry_run:
            results = run_dry(args.fixtures, args.stale_days, args.expiry_days)
        else:
            results = run_live(args.stale_days, args.expiry_days)
    except (EnvironmentError, RuntimeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = build_report(results, mode=mode, stale_days=args.stale_days, expiry_days=args.expiry_days)
    if not args.quiet:
        print_console(report, results)
    else:
        s = report["summary"]
        print(f"mode={mode} findings={s['total_findings']} skipped={s['checks_skipped']}")

    if args.json:
        write_json(report, args.json)
        print(f"\nJSON report written to {args.json}")
    if args.csv:
        write_csv(results, args.csv)
        print(f"CSV report written to {args.csv}")

    # Exit 1 if any critical/high findings (useful for CI gates on dry-run demos)
    sev = report["summary"]["by_severity"]
    if sev.get("critical") or sev.get("high"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
