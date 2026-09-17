"""Thin Microsoft Graph HTTP client with OData pagination."""

from __future__ import annotations

from typing import Any, Iterator
from urllib.parse import urljoin

import requests

GRAPH_BASE = "https://graph.microsoft.com/v1.0/"
GRAPH_BETA = "https://graph.microsoft.com/beta/"


class GraphPermissionError(PermissionError):
    """Raised when Graph returns 401/403 (missing application permission)."""

    def __init__(self, path: str, status: int, body: str) -> None:
        self.path = path
        self.status = status
        self.body = body
        super().__init__(f"Graph {status} for {path}: {body[:300]}")


class GraphClient:
    """Minimal Graph client. Read-only by convention — never POSTs mutating data."""

    def __init__(self, token: str, session: requests.Session | None = None, timeout: int = 60) -> None:
        self._token = token
        self._session = session or requests.Session()
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "ConsistencyLevel": "eventual",
        }

    def get(self, path: str, *, params: dict[str, Any] | None = None, beta: bool = False) -> dict[str, Any]:
        base = GRAPH_BETA if beta else GRAPH_BASE
        url = path if path.startswith("http") else urljoin(base, path.lstrip("/"))
        resp = self._session.get(url, headers=self._headers(), params=params, timeout=self._timeout)
        if resp.status_code in (401, 403):
            raise GraphPermissionError(path, resp.status_code, resp.text)
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    def get_all(self, path: str, *, params: dict[str, Any] | None = None, beta: bool = False) -> list[dict[str, Any]]:
        """Follow @odata.nextLink until exhausted; return combined value lists."""
        items: list[dict[str, Any]] = []
        data = self.get(path, params=params, beta=beta)
        items.extend(data.get("value") or [])
        next_link = data.get("@odata.nextLink")
        while next_link:
            data = self.get(next_link)
            items.extend(data.get("value") or [])
            next_link = data.get("@odata.nextLink")
        return items

    def iter_pages(self, path: str, *, params: dict[str, Any] | None = None, beta: bool = False) -> Iterator[dict[str, Any]]:
        for item in self.get_all(path, params=params, beta=beta):
            yield item
