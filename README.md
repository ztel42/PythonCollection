# PythonCollection

Collected Python projects from my portfolio.

Each folder is a straight copy of the original repository. Project code and file contents were not modified.

| Project | Original repo |
| --- | --- |
| `EntraHygieneChecker` | *(new — lives in this collection)* https://github.com/ztel42/PythonCollection/tree/main/EntraHygieneChecker |
| `FileIntegrityCheckerSHA256` | https://github.com/ztel42/FileIntegrityCheckerSHA256 |
| `PythonCPUusageLogger` | https://github.com/ztel42/PythonCPUusageLogger |
| `PythonSharePointAutoPull` | https://github.com/ztel42/PythonSharePointAutoPull |
| `PythonSharePointLibraryAutoZip` | https://github.com/ztel42/PythonSharePointLibraryAutoZip |
| `ztelCyberDefensePlatform` | https://github.com/ztel42/ztelCyberDefensePlatform |

## Changelog

### Thu Sep 17, 2026 ET — Security hardening
- Path traversal harden SharePointLibraryAutoZip (`safe_join` / basename + reject `..` / separators; resolve under intended root before write)
- OData datetime validation SharePointListPullAuto (parse/validate UTC ISO before filter interpolation)
- Bump requests for CVE-2024-47081 / prefer 2.33.0 (also covers CVE-2026-25645): `requests==2.32.3` → `requests==2.33.0` in EntraHygieneChecker and nested ztelCyberDefensePlatform pins
