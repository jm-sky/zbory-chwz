"""API router for the people directory (email export + person browser) module."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.churches.db_models import PersonDB
from app.modules.directory.db_models import PersonChangeLogDB
from app.modules.directory.repositories import (
    Affiliation,
    DirectoryRepository,
    get_directory_repository,
)
from app.modules.directory.schemas import (
    PERSON_FIELD_LABELS,
    DirectoryExportResponse,
    DirectoryFiltersResponse,
    DirectoryOption,
    DirectoryPersonResponse,
    PersonAffiliationResponse,
    PersonBrowseResponse,
    PersonChangeLogBatch,
    PersonChangeLogFieldChange,
    PersonChangeLogResponse,
    PersonListResponse,
    PersonMergeRequest,
    PersonUpdateRequest,
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


def _group_person_change_log_by_batch(rows: list[PersonChangeLogDB]) -> list[PersonChangeLogBatch]:
    """Group flat change-log rows (as returned by the repo, batch-ordered) into batches."""
    batches: dict[str, list[PersonChangeLogDB]] = {}
    order: list[str] = []
    for row in rows:
        if row.batch_id not in batches:
            batches[row.batch_id] = []
            order.append(row.batch_id)
        batches[row.batch_id].append(row)

    return [
        PersonChangeLogBatch(
            batch_id=batch_id,
            source=batches[batch_id][0].source,  # type: ignore[arg-type]
            actor_label=batches[batch_id][0].actor_label,
            created_at=max(row.created_at for row in batches[batch_id]),
            changes=[
                PersonChangeLogFieldChange(
                    id=row.id,
                    field=row.field,  # type: ignore[arg-type]
                    field_label=PERSON_FIELD_LABELS.get(row.field, row.field),
                    old_value=row.old_value,
                    new_value=row.new_value,
                )
                for row in batches[batch_id]
            ],
        )
        for batch_id in order
    ]


def _person_response(person: PersonDB, affiliations: list[Affiliation]) -> PersonBrowseResponse:
    return PersonBrowseResponse(
        id=person.id,
        firstName=person.first_name,
        lastName=person.last_name,
        email=person.email,
        phone=person.phone,
        affiliations=[PersonAffiliationResponse(kind=kind, label=label, context=context) for kind, label, context in affiliations],
    )


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


@router.get("/persons", response_model=PersonListResponse)
async def list_persons(
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
    q: str | None = Query(default=None),
) -> PersonListResponse:
    allowed = await _require_access(current_user, repo)

    persons = await repo.list_persons(allowed, query=q)
    affiliations = await repo.get_affiliations([p.id for p in persons])

    return PersonListResponse(persons=[_person_response(p, affiliations.get(p.id, [])) for p in persons])


async def _get_person_in_scope(person_id: str, allowed: set[str] | None, repo: DirectoryRepository) -> PersonDB:
    person = await repo.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    if not await repo.person_in_scope(person_id, allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return person


@router.get("/persons/{person_id}", response_model=PersonBrowseResponse)
async def get_person(
    person_id: str,
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
) -> PersonBrowseResponse:
    allowed = await _require_access(current_user, repo)
    person = await _get_person_in_scope(person_id, allowed, repo)

    affiliations = await repo.get_affiliations([person_id])
    return _person_response(person, affiliations.get(person_id, []))


@router.patch("/persons/{person_id}", response_model=PersonBrowseResponse)
async def update_person(
    person_id: str,
    payload: PersonUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
) -> PersonBrowseResponse:
    allowed = await _require_access(current_user, repo)
    await _get_person_in_scope(person_id, allowed, repo)

    person = await repo.update_person(person_id, payload, actor_label=current_user.name, actor_user_id=current_user.id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    affiliations = await repo.get_affiliations([person_id])
    return _person_response(person, affiliations.get(person_id, []))


@router.get(
    "/persons/{person_id}/change-log",
    response_model=PersonChangeLogResponse,
    summary="Change history for a person's directory record",
    description="Visible to anyone with ACL access to the people directory (same access as browsing/editing persons).",
)
async def get_person_change_log(
    person_id: str,
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> PersonChangeLogResponse:
    allowed = await _require_access(current_user, repo)
    await _get_person_in_scope(person_id, allowed, repo)

    rows = await repo.get_change_log(person_id, skip=skip, limit=limit)
    total = await repo.count_change_log_batches(person_id)
    return PersonChangeLogResponse(batches=_group_person_change_log_by_batch(rows), total=total)


@router.post("/persons/merge", response_model=PersonBrowseResponse)
async def merge_persons(
    payload: PersonMergeRequest,
    current_user: CurrentUser,
    repo: Annotated[DirectoryRepository, Depends(get_directory_repository)],
) -> PersonBrowseResponse:
    if payload.keepPersonId == payload.mergePersonId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge a person into themself",
        )

    allowed = await _require_access(current_user, repo)
    await _get_person_in_scope(payload.keepPersonId, allowed, repo)
    await _get_person_in_scope(payload.mergePersonId, allowed, repo)

    person = await repo.merge_persons(payload.keepPersonId, payload.mergePersonId)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    affiliations = await repo.get_affiliations([person.id])
    return _person_response(person, affiliations.get(person.id, []))
