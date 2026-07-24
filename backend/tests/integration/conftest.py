"""Integration-wide fixtures.

CSRF: zbory-chwz has many per-file ``AsyncClient`` fixtures against ``main.app``.
Autouse-wrap ``httpx.AsyncClient.request`` so unsafe methods obtain CSRF via
GET ``/api/auth/csrf-token`` and send ``X-CSRF-Token`` (cookie is jar-managed).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import httpx
import pytest

from app.core.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _header_missing(headers: Mapping[str, Any] | None) -> bool:
    if not headers:
        return True
    return CSRF_HEADER_NAME not in headers and CSRF_HEADER_NAME.lower() not in {
        str(k).lower() for k in headers
    }


@pytest.fixture(autouse=True)
def _inject_csrf_on_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    original_request = httpx.AsyncClient.request

    async def request_with_csrf(
        self: httpx.AsyncClient,
        method: str,
        url: httpx.URL | str,
        **kwargs: Any,
    ) -> httpx.Response:
        if method.upper() not in _SAFE_METHODS:
            raw_headers = kwargs.get("headers")
            headers: MutableMapping[str, Any] = dict(raw_headers or {})
            if _header_missing(headers):
                token = self.cookies.get(CSRF_COOKIE_NAME)
                if not token:
                    csrf_resp = await original_request(self, "GET", "/api/auth/csrf-token")
                    token = csrf_resp.cookies.get(CSRF_COOKIE_NAME)
                    if not token:
                        try:
                            token = csrf_resp.json().get("csrf_token")
                        except Exception:
                            token = None
                if token:
                    headers[CSRF_HEADER_NAME] = token
                    kwargs["headers"] = headers
        return await original_request(self, method, url, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "request", request_with_csrf)
