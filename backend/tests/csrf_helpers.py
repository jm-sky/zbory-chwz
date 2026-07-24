"""CSRF helpers for tests hitting the full app (double-submit cookie).

Integration suites build many local ``AsyncClient`` fixtures; an autouse
patch in ``tests/integration/conftest.py`` wraps ``httpx.AsyncClient.request``.
The shared ``TestClient`` fixture in ``tests/conftest.py`` uses
``install_csrf_on_test_client``.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient

from app.core.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def csrf_headers_for_test_client(client: TestClient) -> dict[str, str]:
    """Fetch CSRF via GET /api/auth/csrf-token and return header dict."""
    response = client.get("/api/auth/csrf-token")
    assert response.status_code == status.HTTP_200_OK
    token = response.cookies.get(CSRF_COOKIE_NAME) or response.json()["csrf_token"]
    assert token
    return {CSRF_HEADER_NAME: token}


def _header_missing(headers: Mapping[str, Any] | None) -> bool:
    if not headers:
        return True
    return CSRF_HEADER_NAME not in headers and CSRF_HEADER_NAME.lower() not in {
        str(k).lower() for k in headers
    }


def install_csrf_on_test_client(client: TestClient) -> TestClient:
    """Wrap TestClient.request so unsafe methods get ``X-CSRF-Token``."""
    original_request = client.request

    def request(method: str, url: str, **kwargs: Any) -> Any:
        if method.upper() not in _SAFE_METHODS:
            headers: MutableMapping[str, Any] = dict(kwargs.get("headers") or {})
            if _header_missing(headers):
                token = client.cookies.get(CSRF_COOKIE_NAME)
                if not token:
                    csrf_resp = original_request("GET", "/api/auth/csrf-token")
                    token = csrf_resp.cookies.get(CSRF_COOKIE_NAME) or csrf_resp.json()["csrf_token"]
                headers[CSRF_HEADER_NAME] = token
                kwargs["headers"] = headers
        return original_request(method, url, **kwargs)

    client.request = request  # type: ignore[method-assign]
    return client
