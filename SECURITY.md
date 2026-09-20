# Security Policy

## Supported versions
Security fixes are applied to the default branch of this repository.

## Reporting a vulnerability
Please do **not** open a public issue for security problems.

Report privately via GitHub Security Advisories for this repository (Security → Advisories → Report a vulnerability), or contact the owner (@ztel42) with enough detail to reproduce.

We aim to acknowledge reports within 7 days and share a remediation plan when feasible.

## Baseline controls
This repository aims to keep:
- Dependabot security updates / vulnerability alerts enabled when available
- Secret scanning enabled when available for the plan/visibility
- No hardcoded secrets; use environment variables or a secret store
- Dependency pins kept current for known Critical/High CVEs

Last aligned: Sat Sep 19, 2026 ET

## Dependency updates
- Sun Sep 20, 2026 ET — Dependabot: bump requests to 2.33.0 (CVE-2024-47081, CVE-2026-25645); bump pytest to >=9.0.3 (CVE-2025-71176)
