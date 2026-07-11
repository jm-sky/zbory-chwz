"""API router for the people directory (email export) module."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.directory.repositories import (
    DirectoryRepository,
    get_directory_repository,
)
from app.modules.directory.schemas import (
    DirectoryExportResponse,
    DirectoryFiltersResponse,
    DirectoryOption,
    DirectoryPersonResponse,
)
from app.modules.groups.repositories import GroupRepository, get_group_repository

router = APIRouter(prefix="/people-directory", tags=["People Directory"])


async def _require_access(current_user: User, repo: DirectoryRepository) -> set[str] | None:
    allowed = await repo.get_allowed_church_ids(current_user)
    if allowed is not None and not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No ACL role grants access to the people directory",
        )
    return allowed


@router.get("/filters", response_model=DirectoryFiltersResponse)
async def get_filters(
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
    group_repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> DirectoryFiltersResponse:
    allowed = await _require_access(current_user, repo)

    regions = await repo.list_available_regions(allowed)
    service_types = await repo.list_service_types()
    can_manage_all = current_user.isAdmin or current_user.isOwner
    groups = await group_repo.list_groups(user_id=current_user.id, can_manage_all=can_manage_all)

    return DirectoryFiltersResponse(
        regions=[DirectoryOption(id=r.id, name=r.name) for r in regions],
        serviceTypes=[DirectoryOption(id=s.id, name=s.name) for s in service_types],
        groups=[DirectoryOption(id=g.id, name=g.name) for g in groups],
    )


@router.get("/export", response_model=DirectoryExportResponse)
async def export_persons(
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
    regionIds: Annotated[list[str], Query()] = [],  # noqa: B006
    serviceTypeIds: Annotated[list[str], Query()] = [],  # noqa: B006
    groupIds: Annotated[list[str], Query()] = [],  # noqa: B006
) -> DirectoryExportResponse:
    allowed = await _require_access(current_user, repo)

    persons = await repo.export_persons(
        allowed,
        region_ids=regionIds,
        service_type_ids=serviceTypeIds,
        group_ids=groupIds,
    )

    return DirectoryExportResponse(persons=[DirectoryPersonResponse.model_validate(p) for p in persons])
