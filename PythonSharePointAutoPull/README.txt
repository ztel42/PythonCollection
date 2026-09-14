Overview
This Python script connects to a SharePoint Online list, retrieves items added since the last check, and appends them to an Excel file. It uses Office365-REST-Python-Client and pandas.

Prerequisites
- pip install Office365-REST-Python-Client pandas openpyxl
- Azure AD app registration with least-privilege SharePoint permissions (for example Sites.Selected or Sites.Read.All as appropriate)
- App-only client credentials (client ID + client secret or certificate). Prefer certificates in production.

Required environment variables (do not hardcode secrets in source):
  SHAREPOINT_CLIENT_ID
  SHAREPOINT_CLIENT_SECRET
  SHAREPOINT_SITE_URL

Optional:
  SHAREPOINT_LIST_TITLE (default YourListTitle)
  SHAREPOINT_OUTPUT_XLSX (default output.xlsx)
  SHAREPOINT_LAST_CHECKED_FILE (default last_checked.txt)

How It Works
1. Reads last checked time from a local file
2. Authenticates with SharePoint using client credentials from the environment
3. Queries items created after that timestamp
4. Appends rows to Excel and updates the last checked time

Security notes
- Never commit real client secrets. Use environment variables, a secret store, or CI secrets.
- Prefer app-only auth with least privilege. Do NOT disable MFA to make username/password auth work.
- Username/password auth against SharePoint Online is discouraged and often blocked when MFA is enabled; stick to app registrations.


Changelog
2026-09-07 — Security hardening
- Client ID, client secret, and site URL now come from required environment variables (no hardcoded secrets in source)
- README no longer suggests disabling MFA; documents app-only least-privilege auth instead
- Added .gitignore for .env and generated outputs
