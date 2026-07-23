"""API router for people groups."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import AdminOrOwnerUser, CurrentUser
from app.modules.groups.db_models import PeopleGroupDB, PeopleGroupMembershipDB
from app.modules.groups.repositories import GroupRepository, get_group_repository
from app.modules.groups.schemas import (
    GroupCreateRequest,
    GroupDetailResponse,
    GroupMembershipCreateRequest,
    GroupMembershipResponse,
    GroupMembershipUpdateRequest,
    GroupResponse,
    GroupUpdateRequest,
)

router = APIRouter(prefix="/people-groups", tags=["People Groups"])


def _active_member_count(group: PeopleGroupDB) -> int:
    return sum(1 for m in group.memberships if m.left_at is None)


def _group_response(group: PeopleGroupDB) -> GroupResponse:
    response = GroupResponse.model_validate(group)
    response.memberCount = _active_member_count(group)
    return response


def _membership_response(
    membership: PeopleGroupMembershipDB,
) -> GroupMembershipResponse:
    return GroupMembershipResponse.model_validate(membership)


def _group_detail_response(group: PeopleGroupDB) -> GroupDetailResponse:
    response = GroupDetailResponse.model_validate(group)
    response.memberCount = _active_member_count(group)
    response.memberships = [_membership_response(m) for m in group.memberships]
    return response


async def _get_visible_group(
    group_id: str,
    current_user: CurrentUser,
    repo: GroupRepository,
) -> PeopleGroupDB:
    group = await repo.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    can_manage_all = current_user.isAdmin or current_user.isOwner
    if not repo.can_view_group(group, user_id=current_user.id, can_manage_all=can_manage_all):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return group


async def _get_manageable_group(
    group_id: str,
    current_user: CurrentUser,
    repo: GroupRepository,
) -> PeopleGroupDB:
    group = await repo.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    can_manage_all = current_user.isAdmin or current_user.isOwner
    if not repo.can_manage_members(group, user_id=current_user.id, can_manage_all=can_manage_all):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return group


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    current_user: CurrentUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> list[GroupResponse]:
    can_manage_all = current_user.isAdmin or current_user.isOwner
    groups = await repo.list_groups(user_id=current_user.id, can_manage_all=can_manage_all)
    return [_group_response(g) for g in groups]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreateRequest,
    current_user: AdminOrOwnerUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> GroupResponse:
    _ = current_user
    group = await repo.create_group(payload)
    return _group_response(group)


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: str,
    current_user: CurrentUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> GroupDetailResponse:
    group = await _get_visible_group(group_id, current_user, repo)
    return _group_detail_response(group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    payload: GroupUpdateRequest,
    current_user: AdminOrOwnerUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> GroupResponse:
    _ = current_user
    group = await repo.update_group(group_id, payload)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return _group_response(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    current_user: AdminOrOwnerUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> None:
    _ = current_user
    if not await repo.delete_group(group_id):
        raise HTTPException(status_code=404, detail="Group not found")


@router.post(
    "/{group_id}/memberships",
    response_model=GroupMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_membership(
    group_id: str,
    payload: GroupMembershipCreateRequest,
    current_user: CurrentUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> GroupMembershipResponse:
    await _get_manageable_group(group_id, current_user, repo)
    membership = await repo.add_membership(group_id, payload)
    return _membership_response(membership)


@router.patch(
    "/{group_id}/memberships/{membership_id}",
    response_model=GroupMembershipResponse,
)
async def update_membership(
    group_id: str,
    membership_id: str,
    payload: GroupMembershipUpdateRequest,
    current_user: CurrentUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> GroupMembershipResponse:
    await _get_manageable_group(group_id, current_user, repo)
    membership = await repo.update_membership(group_id, membership_id, payload)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    return _membership_response(membership)


@router.delete(
    "/{group_id}/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_membership(
    group_id: str,
    membership_id: str,
    current_user: CurrentUser,
    repo: Annotated[GroupRepository, Depends(get_group_repository)],
) -> None:
    await _get_manageable_group(group_id, current_user, repo)
    if not await repo.remove_membership(group_id, membership_id):
        raise HTTPException(status_code=404, detail="Membership not found")
