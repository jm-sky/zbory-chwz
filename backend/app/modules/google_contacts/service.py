"""Business logic for connecting Google Contacts and loading/filtering contacts.

Phase 1 of docs/plans/2026-07-10--google-contacts-sync.md: readonly connection
+ text-filtered contact list. Classification/mapping screen (Phase 2), import
(Phase 3) and export (Phase 4) build on top of this.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import Depends, HTTPException, status

from app.modules.google_contacts.classification import (
    FILTER_KEYWORDS,
    classify_contact,
    contact_matches_filter,
)
from app.modules.google_contacts.crypto_utils import decrypt_token, encrypt_token
from app.modules.google_contacts.db_models import GoogleContactsConnectionDB
from app.modules.google_contacts.oauth_provider import (
    SCOPE_WRITE,
    GoogleContactsOAuthProvider,
    google_contacts_oauth_provider,
)
from app.modules.google_contacts.repositories import (
    GoogleContactsRepository,
    get_google_contacts_repository,
)
from app.modules.google_contacts.schemas import (
    GoogleContactsConnectionResponse,
    GoogleContactsConnectionScope,
    GoogleContactSuggestion,
)

# Refresh the access token a bit before it actually expires.
TOKEN_REFRESH_MARGIN = timedelta(minutes=2)


class GoogleContactsService:
    def __init__(
        self,
        repository: GoogleContactsRepository,
        provider: GoogleContactsOAuthProvider,
    ) -> None:
        self.repository = repository
        self.provider = provider

    def generate_state(self) -> str:
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str, *, write: bool = False) -> str:
        return self.provider.get_authorization_url(state, write=write)

    async def complete_connection(self, *, user_id: str, code: str) -> GoogleContactsConnectionDB:
        token_response = await self.provider.exchange_code_for_token(code)

        if not token_response.refreshToken:
            existing = await self.repository.get_active_connection(user_id)
            if not existing or not existing.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=("Google did not return a refresh token. Revoke access at " "https://myaccount.google.com/permissions and try connecting again."),
                )

        expires_at = None
        if token_response.expiresIn:
            expires_at = datetime.now(UTC) + timedelta(seconds=token_response.expiresIn)

        granted_scopes = token_response.scope.split()
        scope = "readonly_write" if SCOPE_WRITE in granted_scopes else "readonly"

        return await self.repository.upsert_connection(
            user_id=user_id,
            scope=scope,
            access_token=encrypt_token(token_response.accessToken),
            refresh_token=(encrypt_token(token_response.refreshToken) if token_response.refreshToken else None),
            expires_at=expires_at,
        )

    async def get_connection_status(self, user_id: str) -> GoogleContactsConnectionResponse:
        connection = await self.repository.get_active_connection(user_id)
        if not connection:
            return GoogleContactsConnectionResponse(connected=False)
        return GoogleContactsConnectionResponse(
            connected=True,
            scope=cast(GoogleContactsConnectionScope, connection.scope),
            connectedAt=connection.connected_at,
            expiresAt=connection.expires_at,
        )

    async def disconnect(self, user_id: str) -> bool:
        return await self.repository.revoke_connection(user_id)

    async def _get_valid_access_token(self, connection: GoogleContactsConnectionDB) -> str:
        expires_at = connection.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            # SQLite drops tzinfo on round-trip; the column is always stored as UTC.
            expires_at = expires_at.replace(tzinfo=UTC)
        needs_refresh = expires_at is not None and expires_at - TOKEN_REFRESH_MARGIN <= datetime.now(UTC)
        if not needs_refresh:
            return decrypt_token(connection.access_token)

        if not connection.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Google Contacts connection expired and has no refresh token. Reconnect.",
            )

        token_response = await self.provider.refresh_access_token(decrypt_token(connection.refresh_token))
        expires_at = None
        if token_response.expiresIn:
            expires_at = datetime.now(UTC) + timedelta(seconds=token_response.expiresIn)

        await self.repository.update_tokens(
            connection,
            access_token=encrypt_token(token_response.accessToken),
            expires_at=expires_at,
        )
        return token_response.accessToken

    async def load_filtered_contacts(
        self,
        user_id: str,
        keywords: Sequence[str] = FILTER_KEYWORDS,
    ) -> tuple[list[GoogleContactSuggestion], int]:
        if not any(keyword.strip() for keyword in keywords):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one filter keyword is required.",
            )

        connection = await self.repository.get_active_connection(user_id)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google Contacts connection. Connect first.",
            )

        access_token = await self._get_valid_access_token(connection)
        raw_contacts = await self.provider.list_connections(access_token)

        suggestions = [_to_suggestion(contact, keywords) for contact in raw_contacts if contact_matches_filter(contact, keywords)]
        return suggestions, len(raw_contacts)


def _to_suggestion(contact: dict, keywords: Sequence[str] = FILTER_KEYWORDS) -> GoogleContactSuggestion:
    names = contact.get("names") or []
    organizations = contact.get("organizations") or []
    emails = contact.get("emailAddresses") or []
    phones = contact.get("phoneNumbers") or []
    bios = contact.get("biographies") or []
    addresses = contact.get("addresses") or []
    address = addresses[0] if addresses else {}
    name = names[0] if names else {}

    return GoogleContactSuggestion(
        resourceName=contact.get("resourceName", ""),
        displayName=name.get("displayName"),
        firstName=name.get("givenName"),
        lastName=name.get("familyName"),
        organizationName=organizations[0].get("name") if organizations else None,
        emailAddresses=[e.get("value") for e in emails if e.get("value")],
        phoneNumbers=[p.get("value") for p in phones if p.get("value")],
        notes=bios[0].get("value") if bios else None,
        suggestedType=classify_contact(contact, keywords),
        addressStreet=address.get("streetAddress"),
        addressCity=address.get("city"),
        addressPostalCode=address.get("postalCode"),
        addressProvince=address.get("region"),
        addressCountry=address.get("countryCode"),
    )


def get_google_contacts_service(
    repository: GoogleContactsRepository = Depends(get_google_contacts_repository),
) -> GoogleContactsService:
    return GoogleContactsService(repository, google_contacts_oauth_provider)
