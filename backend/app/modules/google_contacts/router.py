"""API router for the Google Contacts (People API) connection and import source.

Phase 1: connect (readonly), status, disconnect, load+filter contacts.
Restricted to admin/owner per docs/plans/2026-07-10--google-contacts-sync.md
decision #1 — only admin/owner can import Google Contacts into the database.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.modules.auth.decorators import rate_limit
from app.modules.auth.dependencies import AdminOrOwnerUser
from app.modules.google_contacts.schemas import (
    GoogleContactsAuthUrlResponse,
    GoogleContactsCallbackRequest,
    GoogleContactsConnectionResponse,
    GoogleContactsListResponse,
)
from app.modules.google_contacts.service import (
    GoogleContactsService,
    get_google_contacts_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-contacts", tags=["Google Contacts"])


@router.post(
    "/auth-url",
    response_model=GoogleContactsAuthUrlResponse,
    summary="Get Google Contacts authorization URL",
    description="Generate the OAuth consent URL to connect Google Contacts (readonly)",
)
@rate_limit("10/minute")
async def get_auth_url(
    current_user: AdminOrOwnerUser,
    service: Annotated[GoogleContactsService, Depends(get_google_contacts_service)],
    request: Request,
) -> GoogleContactsAuthUrlResponse:
    state = service.generate_state()
    auth_url = service.get_authorization_url(state)
    return GoogleContactsAuthUrlResponse(authUrl=auth_url, state=state)


@router.post(
    "/callback",
    response_model=GoogleContactsConnectionResponse,
    summary="Complete Google Contacts connection",
    description="Exchange the OAuth code for tokens and store the connection",
)
@rate_limit("10/minute")
async def callback(
    callback_data: GoogleContactsCallbackRequest,
    current_user: AdminOrOwnerUser,
    service: Annotated[GoogleContactsService, Depends(get_google_contacts_service)],
    request: Request,
) -> GoogleContactsConnectionResponse:
    try:
        await service.complete_connection(user_id=current_user.id, code=callback_data.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return await service.get_connection_status(current_user.id)


@router.get(
    "/connection",
    response_model=GoogleContactsConnectionResponse,
    summary="Get Google Contacts connection status",
)
async def get_connection(
    current_user: AdminOrOwnerUser,
    service: Annotated[GoogleContactsService, Depends(get_google_contacts_service)],
) -> GoogleContactsConnectionResponse:
    return await service.get_connection_status(current_user.id)


@router.delete(
    "/connection",
    summary="Disconnect Google Contacts",
)
@rate_limit("10/minute")
async def disconnect(
    current_user: AdminOrOwnerUser,
    service: Annotated[GoogleContactsService, Depends(get_google_contacts_service)],
    request: Request,
) -> dict[str, str]:
    deleted = await service.disconnect(current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Google Contacts connection",
        )
    return {"message": "Google Contacts connection removed successfully"}


@router.get(
    "/contacts",
    response_model=GoogleContactsListResponse,
    summary="Load and filter Google contacts",
    description='Fetch the connected Google account\'s contacts and filter for "zbór"/"chwz" matches',
)
async def list_contacts(
    current_user: AdminOrOwnerUser,
    service: Annotated[GoogleContactsService, Depends(get_google_contacts_service)],
) -> GoogleContactsListResponse:
    suggestions, total_fetched = await service.load_filtered_contacts(current_user.id)
    return GoogleContactsListResponse(
        contacts=suggestions,
        totalFetched=total_fetched,
        matchedCount=len(suggestions),
    )
