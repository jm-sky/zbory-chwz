"""Google Contacts (People API) OAuth + API client.

Deliberately separate from ``app.core.oauth.GoogleOAuthProvider`` (login):
connecting Google Contacts is an independent action any admin/owner takes
after they're already logged in (by any method), and it requests its own
scope via incremental authorization — see docs/plans/2026-07-10--google-contacts-sync.md
decision #10. It reuses the same Google OAuth client (client_id/secret) as
login, but a dedicated redirect URI.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_PEOPLE_API_BASE = "https://people.googleapis.com/v1"

SCOPE_READONLY = "https://www.googleapis.com/auth/contacts.readonly"
SCOPE_WRITE = "https://www.googleapis.com/auth/contacts"

# Fields we need to classify a contact as church vs person and to match/import it.
PERSON_FIELDS = "names,organizations,emailAddresses,phoneNumbers,addresses,biographies"


class GoogleContactsTokenResponse(BaseModel):
    """OAuth token exchange response (People API)."""

    accessToken: str
    tokenType: str
    scope: str
    expiresIn: int | None = None
    refreshToken: str | None = None


class GoogleContactsOAuthProvider:
    """OAuth authorization + People API client for the Contacts connection."""

    def __init__(self) -> None:
        self.client_id = settings.oauth.google_client_id
        self.client_secret = settings.oauth.google_client_secret
        self.redirect_uri = settings.oauth.google_contacts_redirect_uri

    def get_authorization_url(self, state: str, *, write: bool = False) -> str:
        """Build the Google consent URL.

        ``write=True`` also requests the write scope (incremental auth, used
        by the export flow) in addition to readonly.
        """

        scopes = [SCOPE_READONLY, SCOPE_WRITE] if write else [SCOPE_READONLY]
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> GoogleContactsTokenResponse:
        """Exchange authorization code for access/refresh tokens."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise ValueError(f"Google Contacts OAuth error: {data.get('error_description', data['error'])}")

            return GoogleContactsTokenResponse(
                accessToken=data["access_token"],
                tokenType=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
                expiresIn=data.get("expires_in"),
                refreshToken=data.get("refresh_token"),
            )

    async def refresh_access_token(self, refresh_token: str) -> GoogleContactsTokenResponse:
        """Get a new access token using a stored refresh token."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise ValueError(f"Google Contacts token refresh error: {data.get('error_description', data['error'])}")

            return GoogleContactsTokenResponse(
                accessToken=data["access_token"],
                tokenType=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
                expiresIn=data.get("expires_in"),
                # Google does not re-issue a refresh token on refresh
                refreshToken=refresh_token,
            )

    async def list_connections(self, access_token: str) -> list[dict]:
        """Fetch all of the user's contacts (paginated) from the People API."""

        contacts: list[dict] = []
        page_token: str | None = None

        async with httpx.AsyncClient() as client:
            while True:
                params: dict[str, str | int] = {
                    "personFields": PERSON_FIELDS,
                    "pageSize": 1000,
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    f"{GOOGLE_PEOPLE_API_BASE}/people/me/connections",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

                contacts.extend(data.get("connections", []))
                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return contacts


google_contacts_oauth_provider = GoogleContactsOAuthProvider()
