"""Repository layer for people groups."""

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.churches.db_models import PersonDB
from app.modules.churches.slug_utils import slugify
from app.modules.groups.db_models import PeopleGroupDB, PeopleGroupMembershipDB
from app.modules.groups.schemas import (
    GroupCreateRequest,
    GroupMembershipCreateRequest,
    GroupMembershipUpdateRequest,
    GroupUpdateRequest,
)


class GroupRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_groups(self, *, user_id: str, can_manage_all: bool) -> Sequence[PeopleGroupDB]:
        stmt = select(PeopleGroupDB).options(selectinload(PeopleGroupDB.memberships))
        if not can_manage_all:
            stmt = stmt.where(
                or_(
                    PeopleGroupDB.visibility != "private",
                    PeopleGroupDB.steward_user_id == user_id,
                )
            )
        stmt = stmt.order_by(PeopleGroupDB.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_group(self, group_id: str) -> PeopleGroupDB | None:
        result = await self.db.execute(select(PeopleGroupDB).where(PeopleGroupDB.id == group_id).options(selectinload(PeopleGroupDB.memberships).selectinload(PeopleGroupMembershipDB.person)))
        return result.scalar_one_or_none()

    def can_view_group(self, group: PeopleGroupDB, *, user_id: str, can_manage_all: bool) -> bool:
        if group.visibility != "private":
            return True
        return can_manage_all or group.steward_user_id == user_id

    def can_manage_members(self, group: PeopleGroupDB, *, user_id: str, can_manage_all: bool) -> bool:
        return can_manage_all or group.steward_user_id == user_id

    async def create_group(self, payload: GroupCreateRequest) -> PeopleGroupDB:
        slug = payload.slug or slugify(payload.name)
        existing = await self.db.execute(select(PeopleGroupDB).where(PeopleGroupDB.slug == slug))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A group with this slug already exists",
            )

        group = PeopleGroupDB(
            id=generate_id(),
            name=payload.name,
            slug=slug,
            description=payload.description,
            scope_type=payload.scopeType,
            scope_id=payload.scopeId,
            visibility=payload.visibility,
            steward_user_id=payload.stewardUserId,
        )
        self.db.add(group)
        await self.db.commit()
        created = await self.get_group(group.id)
        assert created is not None
        return created

    async def update_group(self, group_id: str, payload: GroupUpdateRequest) -> PeopleGroupDB | None:
        group = await self.get_group(group_id)
        if not group:
            return None

        if payload.name is not None:
            group.name = payload.name
        if payload.slug is not None:
            group.slug = payload.slug
        if payload.description is not None:
            group.description = payload.description
        if payload.scopeType is not None:
            group.scope_type = payload.scopeType
        if payload.scopeId is not None:
            group.scope_id = payload.scopeId
        if payload.visibility is not None:
            group.visibility = payload.visibility
        if payload.stewardUserId is not None:
            group.steward_user_id = payload.stewardUserId or None

        group.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(group)
        return await self.get_group(group_id)

    async def delete_group(self, group_id: str) -> bool:
        group = await self.get_group(group_id)
        if not group:
            return False
        await self.db.delete(group)
        await self.db.commit()
        return True

    async def _resolve_person(self, payload: GroupMembershipCreateRequest) -> PersonDB:
        if payload.personId:
            result = await self.db.execute(select(PersonDB).where(PersonDB.id == payload.personId))
            person = result.scalar_one_or_none()
            if not person:
                raise HTTPException(status_code=404, detail="Person not found")
            return person

        person = PersonDB(
            id=generate_id(),
            first_name=payload.firstName,
            last_name=payload.lastName,
            email=payload.email,
            phone=payload.phone,
        )
        self.db.add(person)
        await self.db.flush()
        return person

    async def add_membership(self, group_id: str, payload: GroupMembershipCreateRequest) -> PeopleGroupMembershipDB:
        person = await self._resolve_person(payload)

        existing = await self.db.execute(
            select(PeopleGroupMembershipDB).where(
                PeopleGroupMembershipDB.group_id == group_id,
                PeopleGroupMembershipDB.person_id == person.id,
                PeopleGroupMembershipDB.left_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Person is already an active member of this group",
            )

        membership = PeopleGroupMembershipDB(
            id=generate_id(),
            group_id=group_id,
            person_id=person.id,
            role_label=payload.roleLabel,
        )
        self.db.add(membership)
        await self.db.commit()

        result = await self.db.execute(select(PeopleGroupMembershipDB).where(PeopleGroupMembershipDB.id == membership.id).options(selectinload(PeopleGroupMembershipDB.person)))
        return result.scalar_one()

    async def update_membership(self, group_id: str, membership_id: str, payload: GroupMembershipUpdateRequest) -> PeopleGroupMembershipDB | None:
        result = await self.db.execute(
            select(PeopleGroupMembershipDB)
            .where(
                PeopleGroupMembershipDB.id == membership_id,
                PeopleGroupMembershipDB.group_id == group_id,
            )
            .options(selectinload(PeopleGroupMembershipDB.person))
        )
        membership = result.scalar_one_or_none()
        if not membership:
            return None
        if payload.roleLabel is not None:
            membership.role_label = payload.roleLabel
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_membership(self, group_id: str, membership_id: str) -> bool:
        result = await self.db.execute(
            select(PeopleGroupMembershipDB).where(
                PeopleGroupMembershipDB.id == membership_id,
                PeopleGroupMembershipDB.group_id == group_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership or membership.left_at is not None:
            return False
        membership.left_at = datetime.now(UTC)
        await self.db.commit()
        return True


def get_group_repository(db: AsyncSession = Depends(get_db)) -> GroupRepository:
    return GroupRepository(db)
