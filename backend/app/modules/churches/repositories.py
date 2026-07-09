"""Repository layer for church hierarchy."""

import logging
import secrets
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.auth.auth_utils import get_password_hash
from app.modules.auth.db_models import UserDB
from app.modules.churches.db_models import (
    BranchDB,
    ChurchDB,
    ChurchSlugAliasDB,
    CityAliasDB,
    CommunityDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.schemas import (
    BranchCreateRequest,
    BranchUpdateRequest,
    ServiceAssignmentCreateRequest,
    ServiceAssignmentUpdateRequest,
)
from app.modules.churches.seed_data import PASTOR_SERVICE_SLUGS
from app.modules.churches.slug_utils import church_slug, city_slug, country_slug
from app.modules.congregations.db_models import (
    CongregationAddressDB,
    CongregationContactPersonDB,
    CongregationServiceTimeDB,
)
from app.modules.tenants.db_models import TenantDB

logger = logging.getLogger(__name__)


class ChurchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_church_by_id(self, church_id: str) -> ChurchDB | None:
        result = await self.db.execute(select(ChurchDB).where(ChurchDB.id == church_id))
        return result.scalar_one_or_none()

    async def list_regions(self) -> list[RegionDB]:
        result = await self.db.execute(select(RegionDB).order_by(RegionDB.name))
        return list(result.scalars().all())

    async def list_service_types(self) -> list[ServiceTypeDB]:
        result = await self.db.execute(
            select(ServiceTypeDB).order_by(ServiceTypeDB.sort_order)
        )
        return list(result.scalars().all())

    async def get_service_type(self, service_type_id: str) -> ServiceTypeDB | None:
        result = await self.db.execute(
            select(ServiceTypeDB).where(ServiceTypeDB.id == service_type_id)
        )
        return result.scalar_one_or_none()

    async def list_branches(self, church_id: str) -> list[BranchDB]:
        result = await self.db.execute(
            select(BranchDB)
            .where(BranchDB.church_id == church_id)
            .order_by(BranchDB.name)
        )
        return list(result.scalars().all())

    async def create_branch(
        self, church_id: str, payload: BranchCreateRequest
    ) -> BranchDB:
        slug = payload.slug or church_slug(payload.name)
        branch = BranchDB(
            id=generate_id(),
            church_id=church_id,
            name=payload.name,
            slug=slug,
            visibility=payload.visibility,
        )
        self.db.add(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def update_branch(
        self, branch_id: str, payload: BranchUpdateRequest
    ) -> BranchDB | None:
        result = await self.db.execute(select(BranchDB).where(BranchDB.id == branch_id))
        branch = result.scalar_one_or_none()
        if not branch:
            return None
        if payload.name is not None:
            branch.name = payload.name
        if payload.slug is not None:
            branch.slug = payload.slug
        if payload.visibility is not None:
            branch.visibility = payload.visibility
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def delete_branch(self, branch_id: str) -> bool:
        result = await self.db.execute(select(BranchDB).where(BranchDB.id == branch_id))
        branch = result.scalar_one_or_none()
        if not branch:
            return False
        await self.db.delete(branch)
        await self.db.commit()
        return True

    async def search_persons(self, query: str, limit: int = 20) -> list[PersonDB]:
        pattern = f"%{query.strip()}%"
        stmt = (
            select(PersonDB)
            .where(
                or_(
                    PersonDB.first_name.ilike(pattern),
                    PersonDB.last_name.ilike(pattern),
                    PersonDB.email.ilike(pattern),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_person(self, person_id: str) -> PersonDB | None:
        result = await self.db.execute(select(PersonDB).where(PersonDB.id == person_id))
        return result.scalar_one_or_none()

    async def list_service_assignments(
        self, scope_type: str, scope_id: str
    ) -> list[ServiceAssignmentDB]:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
            .order_by(ServiceAssignmentDB.created_at)
        )
        return list(result.scalars().all())

    async def _resolve_person(
        self, payload: ServiceAssignmentCreateRequest
    ) -> PersonDB:
        if payload.personId:
            person = await self.get_person(payload.personId)
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

    async def _maybe_create_user(
        self,
        person: PersonDB,
        payload: ServiceAssignmentCreateRequest,
        service_type: ServiceTypeDB | None,
    ) -> None:
        if person.user_id:
            return

        is_pastor = service_type and service_type.slug in PASTOR_SERVICE_SLUGS
        should_create = payload.createAccount or is_pastor
        if not should_create:
            return

        if not person.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email required to create user account",
            )

        existing = await self.db.execute(
            select(UserDB).where(UserDB.email == person.email.lower().strip())
        )
        user_db = existing.scalar_one_or_none()
        if not user_db:
            full_name = " ".join(
                p for p in (person.first_name, person.last_name) if p
            ).strip() or person.email
            user_db = UserDB(
                id=generate_id(),
                email=person.email.lower().strip(),
                name=full_name,
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                is_active=not is_pastor,
                is_admin=False,
                created_at=datetime.now(UTC),
                is_email_verified=False,
            )
            self.db.add(user_db)
            await self.db.flush()

        person.user_id = user_db.id

    async def create_service_assignment(
        self,
        scope_type: str,
        scope_id: str,
        payload: ServiceAssignmentCreateRequest,
    ) -> ServiceAssignmentDB:
        if not payload.serviceTypeId and not payload.customServiceName:
            raise HTTPException(
                status_code=400,
                detail="serviceTypeId or customServiceName required",
            )

        service_type = None
        if payload.serviceTypeId:
            service_type = await self.get_service_type(payload.serviceTypeId)
            if not service_type:
                raise HTTPException(status_code=404, detail="Service type not found")

        person = await self._resolve_person(payload)
        await self._maybe_create_user(person, payload, service_type)

        assignment = ServiceAssignmentDB(
            id=generate_id(),
            person_id=person.id,
            service_type_id=payload.serviceTypeId,
            custom_service_name=payload.customServiceName,
            description=payload.description,
            scope_type=scope_type,
            scope_id=scope_id,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        loaded = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.id == assignment.id)
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
        )
        return loaded.scalar_one()

    async def update_service_assignment(
        self, assignment_id: str, payload: ServiceAssignmentUpdateRequest
    ) -> ServiceAssignmentDB | None:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.id == assignment_id)
            .options(selectinload(ServiceAssignmentDB.person))
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return None

        if payload.serviceTypeId is not None:
            assignment.service_type_id = payload.serviceTypeId
        if payload.customServiceName is not None:
            assignment.custom_service_name = payload.customServiceName
        if payload.description is not None:
            assignment.description = payload.description

        person = assignment.person
        if person:
            if payload.firstName is not None:
                person.first_name = payload.firstName
            if payload.lastName is not None:
                person.last_name = payload.lastName
            if payload.email is not None:
                person.email = payload.email
            if payload.phone is not None:
                person.phone = payload.phone
            person.updated_at = datetime.now(UTC)

        await self.db.commit()
        reloaded = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.id == assignment_id)
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
        )
        return reloaded.scalar_one_or_none()

    async def delete_service_assignment(self, assignment_id: str) -> bool:
        result = await self.db.execute(
            select(ServiceAssignmentDB).where(ServiceAssignmentDB.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return False
        await self.db.delete(assignment)
        await self.db.commit()
        return True

    async def ensure_church_access(self, church_id: str) -> ChurchDB:
        church = await self.get_church_by_id(church_id)
        if not church:
            raise HTTPException(status_code=404, detail="Church not found")
        return church


def get_church_repository(db: AsyncSession = Depends(get_db)) -> ChurchRepository:
    return ChurchRepository(db)
