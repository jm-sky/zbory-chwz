"""API router for AI-assisted congregation address/contact import from free text."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AdminOrOwnerUser
from app.modules.congregations.email_import_review_service import (
    EmailImportReviewService,
)
from app.modules.congregations.import_service import CongregationImportService
from app.modules.congregations.schemas import (
    EmailImportApproveRequest,
    EmailImportInboxListResponse,
    ImportAnalyzeRequest,
    ImportAnalyzeResponse,
    ImportApplyRequest,
    ImportApplyResponse,
)

router = APIRouter(prefix="/admin/congregations/import", tags=["Congregation Import"])


def get_import_service(db: AsyncSession = Depends(get_db)) -> CongregationImportService:
    return CongregationImportService(db)


def get_review_service(db: AsyncSession = Depends(get_db)) -> EmailImportReviewService:
    return EmailImportReviewService(db)


@router.post(
    "/analyze",
    response_model=ImportAnalyzeResponse,
    summary="Extract and match congregations from pasted text (admin only)",
    description=("Uses AI to extract congregation address/contact data from free-text " "notes, then fuzzy-matches each entry against existing congregations. " "Makes no database changes — returns proposals for review."),
)
async def analyze_import(
    payload: ImportAnalyzeRequest,
    _: AdminOrOwnerUser,
    service: Annotated[CongregationImportService, Depends(get_import_service)],
) -> ImportAnalyzeResponse:
    try:
        return await service.analyze(payload.raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/apply",
    response_model=ImportApplyResponse,
    summary="Apply reviewed congregation import proposals (admin only)",
    description="Creates/updates congregations from admin-reviewed and edited import proposals.",
)
async def apply_import(
    payload: ImportApplyRequest,
    current_user: AdminOrOwnerUser,
    service: Annotated[CongregationImportService, Depends(get_import_service)],
) -> ImportApplyResponse:
    try:
        return await service.apply(payload, owner_user_id=current_user.id, actor_name=current_user.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get(
    "/inbox",
    response_model=EmailImportInboxListResponse,
    summary="List pending clergy e-mail import proposals (admin only)",
    description="E-mails polled from the clergy update mailbox that were not auto-applied and await review.",
)
async def list_inbox(
    _: AdminOrOwnerUser,
    service: Annotated[EmailImportReviewService, Depends(get_review_service)],
) -> EmailImportInboxListResponse:
    return await service.list_pending()


@router.post(
    "/inbox/{message_id}/approve",
    response_model=ImportApplyResponse,
    summary="Apply a reviewed clergy e-mail import proposal (admin only)",
)
async def approve_inbox_item(
    message_id: str,
    payload: EmailImportApproveRequest,
    current_user: AdminOrOwnerUser,
    service: Annotated[EmailImportReviewService, Depends(get_review_service)],
) -> ImportApplyResponse:
    try:
        return await service.approve(message_id, payload, reviewer=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/inbox/{message_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss a clergy e-mail import proposal without applying it (admin only)",
)
async def reject_inbox_item(
    message_id: str,
    current_user: AdminOrOwnerUser,
    service: Annotated[EmailImportReviewService, Depends(get_review_service)],
) -> None:
    await service.reject(message_id, reviewer=current_user)
