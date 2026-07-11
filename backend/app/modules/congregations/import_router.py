"""API router for AI-assisted congregation address/contact import from free text."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AdminOrOwnerUser
from app.modules.congregations.import_service import CongregationImportService
from app.modules.congregations.schemas import (
    ImportAnalyzeRequest,
    ImportAnalyzeResponse,
    ImportApplyRequest,
    ImportApplyResponse,
)

router = APIRouter(prefix="/admin/congregations/import", tags=["Congregation Import"])


def get_import_service(db: AsyncSession = Depends(get_db)) -> CongregationImportService:
    return CongregationImportService(db)


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
        return await service.apply(payload, owner_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
