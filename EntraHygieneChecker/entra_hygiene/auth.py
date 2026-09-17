"""MSAL client-credentials authentication for Microsoft Graph."""

from __future__ import annotations

import os
from dataclasses import dataclass

import msal

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


@dataclass(frozen=True)
class GraphCredentials:
    tenant_id: str
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> "GraphCredentials":
        tenant_id = os.environ.get("AZURE_TENANT_ID", "").strip()
        client_id = os.environ.get("AZURE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("AZURE_CLIENT_SECRET", "").strip()
        missing = [
            name
            for name, value in (
                ("AZURE_TENANT_ID", tenant_id),
                ("AZURE_CLIENT_ID", client_id),
                ("AZURE_CLIENT_SECRET", client_secret),
            )
            if not value
        ]
        if missing:
            raise EnvironmentError(
                "Missing required environment variables: "
                + ", ".join(missing)
                + ". Set them for app-only (client credentials) auth."
            )
        return cls(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)


def acquire_token(creds: GraphCredentials | None = None) -> str:
    """Acquire an app-only access token for Microsoft Graph."""
    creds = creds or GraphCredentials.from_env()
    app = msal.ConfidentialClientApplication(
        client_id=creds.client_id,
        client_credential=creds.client_secret,
        authority=f"https://login.microsoftonline.com/{creds.tenant_id}",
    )
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if not result or "access_token" not in result:
        err = (result or {}).get("error_description") or (result or {}).get("error") or "unknown error"
        raise RuntimeError(f"Failed to acquire Graph token: {err}")
    return result["access_token"]
