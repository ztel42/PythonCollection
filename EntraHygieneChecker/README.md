# EntraHygieneChecker

Read-only **Microsoft Entra ID / Azure AD** security hygiene CLI for portfolio and lab use.

It authenticates with **app-only (client credentials)** to Microsoft Graph, runs hygiene checks, and emits a console summary plus optional JSON/CSV reports. A **`--dry-run`** mode analyzes fixture JSON so CI works without an Azure tenant.

```
========================================================================
  AUTHORIZED TENANTS ONLY  |  READ-ONLY  |  NO WRITES
========================================================================
```

**Author:** Zach Telford ([ztel42](https://github.com/ztel42))

---

## Disclaimer

- Use only on **tenants you own or are explicitly authorized** to assess.
- This tool is **read-only by design**. Do **not** grant it write permissions.
- Findings are hygiene signals, not a full security audit or penetration test.
- Some Graph reports (sign-in activity, MFA registration) may require Microsoft Entra ID P1/P2 or specific licenses.

---

## Features

| Check | What it looks for |
| --- | --- |
| **MFA registration** | Users without MFA registered (`userRegistrationDetails`); soft-skips if `Reports.Read.All` is missing |
| **Guest / external users** | Stale guests (no sign-in beyond *N* days, default 90); disabled guests still present |
| **App / service principal hygiene** | High-privilege Graph application permissions; passwords/certs expired or expiring within *N* days (default 30) |
| **Privileged directory roles** | Members of Global Administrator and other high-risk roles (count + UPNs) |

High-privilege application permissions flagged include:

- `Directory.ReadWrite.All`
- `RoleManagement.ReadWrite.Directory`
- `AppRoleAssignment.ReadWrite.All`
- `Application.ReadWrite.All`
- `Application.ReadWrite.OwnedBy`
- `User.ReadWrite.All`
- `Group.ReadWrite.All`
- `Policy.ReadWrite.ConditionalAccess`

---

## Required Graph application permissions (least privilege)

Register an app in Entra ID and grant **Application** permissions (admin consent). Prefer the minimum set that enables the checks you need:

| Permission | Type | Used for |
| --- | --- | --- |
| `User.Read.All` | Application | Guest / user listing |
| `AuditLog.Read.All` | Application | `signInActivity` on users (stale guests) |
| `Reports.Read.All` | Application | MFA registration report (`userRegistrationDetails`) |
| `Application.Read.All` | Application | Apps, service principals, app role assignments, credentials |
| `RoleManagement.Read.Directory` | Application | Directory role membership (preferred) |
| `Directory.Read.All` | Application | Alternate/broader read for roles & directory objects |

**Do not grant:** any `*.ReadWrite.*`, `RoleManagement.ReadWrite.*`, `AppRoleAssignment.ReadWrite.All`, or similar write permissions to this tool.

If a check receives HTTP 401/403, it is **soft-skipped** with a clear note in the report instead of failing the whole run.

---

## Setup (app registration)

1. Azure Portal → **Microsoft Entra ID** → **App registrations** → **New registration**.
2. Name it e.g. `EntraHygieneChecker-ReadOnly` (single tenant).
3. **Certificates & secrets** → create a client secret; store it securely.
4. **API permissions** → **Microsoft Graph** → **Application permissions** → add the table above → **Grant admin consent**.
5. Note **Application (client) ID**, **Directory (tenant) ID**, and the secret value.

Environment variables:

```bash
export AZURE_TENANT_ID="<tenant-guid>"
export AZURE_CLIENT_ID="<app-client-id>"
export AZURE_CLIENT_SECRET="<secret>"
```

---

## Install

```bash
cd EntraHygieneChecker
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

---

## Usage

### Dry-run (fixtures / CI — no Azure)

```bash
python -m entra_hygiene --dry-run
python -m entra_hygiene --dry-run --json report.json --csv findings.csv
```

### Live tenant (authorized only)

```bash
python -m entra_hygiene
python -m entra_hygiene --stale-days 90 --expiry-days 30 --json out.json --csv out.csv
```

### CLI flags

| Flag | Description |
| --- | --- |
| `--dry-run` | Analyze `tests/fixtures/` JSON; no Graph calls |
| `--fixtures PATH` | Alternate fixture directory |
| `--stale-days N` | Guest stale threshold (default 90) |
| `--expiry-days N` | Credential expiry window (default 30) |
| `--json PATH` | Write full JSON report |
| `--csv PATH` | Write findings CSV |
| `--quiet` | Summary only on console |

Exit codes: `0` ok / no high+critical findings; `1` high or critical findings present; `2` configuration / runtime error.

---

## Tests

```bash
python -m pytest
```

All analyzer tests use fixtures only — no live Graph.

---

## Project layout

```
entra_hygiene/
  auth.py          # MSAL client credentials
  graph.py         # Graph HTTP + pagination
  checks/          # Pure analyzers + live collectors
  report.py        # Console / JSON / CSV
  cli.py           # argparse entrypoint
tests/fixtures/    # Dry-run + unit-test data
```

---

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
