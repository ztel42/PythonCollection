Overview
Downloads a SharePoint Online document library (including subfolders) and packs it into a .zip file.

Prerequisites
- pip install Office365-REST-Python-Client
- Azure AD app registration with least-privilege read access to the target site/library
- App-only client credentials (prefer certificates in production)

Required environment variables (do not hardcode secrets):
  SHAREPOINT_CLIENT_ID
  SHAREPOINT_CLIENT_SECRET
  SHAREPOINT_SITE_URL

Optional:
  SHAREPOINT_LIBRARY_TITLE (default YourLibraryTitle)
  SHAREPOINT_TEMP_DIR (default temp_download)
  SHAREPOINT_OUTPUT_ZIP (default output.zip)

Security notes
- Never commit real client secrets. Use environment variables or a secret store.
- Prefer app-only auth with least privilege. Do NOT disable MFA to unlock password auth.
- Remote file and folder names are sanitized via safe_join (basename + containment under the temp dir) before local writes.


Changelog
2026-09-26 — Path traversal hardening (ET)
- Added safe_join: reject empty/`.`/`..`, separators, and names that escape the download root
- File and subfolder remote names now go through basename + resolve containment before write
- Commit: https://github.com/ztel42/PythonCollection/commit/017c0c1ca80fe428f7801ecf12727f8faca1dae7

2026-09-07 — Security hardening
- Client ID, client secret, and site URL now come from required environment variables (no hardcoded secrets in source)
- README documents secure app-only auth and explicitly avoids MFA-disable guidance
- Added .gitignore for .env, temp downloads, and zip outputs
