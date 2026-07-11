"""Primary congregation card contact via Person + ServiceAssignment."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.churches.db_models import PersonDB, ServiceAssignmentDB, ServiceTypeDB
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import (
    ServiceAssignmentCreateRequest,
    ServiceAssignmentUpdateRequest,
)
from app.modules.churches.seed_data import TITLE_TO_SERVICE_SLUG


def split_person_name(full_name: str) -> tuple[str | None, str | None]:
    parts = full_name.strip().split(None, 1)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def person_display_name(person: PersonDB) -> str:
    return " ".join(part for part in (person.first_name, person.last_name) if part).strip()


def assignment_title(assignment: ServiceAssignmentDB) -> str | None:
    if assignment.service_type:
        return assignment.service_type.name
    return assignment.custom_service_name


def resolve_service_type_for_title(
    title: str | None,
    service_types_by_slug: dict[str, ServiceTypeDB],
) -> tuple[str | None, str | None]:
    if not title:
        return None, None
    normalized = title.strip().lower()
    slug = TITLE_TO_SERVICE_SLUG.get(normalized)
    if slug and slug in service_types_by_slug:
        return service_types_by_slug[slug].id, None
    return None, title.strip()


def pick_primary_card_assignment(
    assignments: list[ServiceAssignmentDB],
) -> ServiceAssignmentDB | None:
    if not assignments:
        return None
    card_visible = [assignment for assignment in assignments if assignment.show_on_list]
    pool = card_visible or assignments
    return min(pool, key=lambda assignment: (assignment.sort_order, assignment.created_at))


async def load_service_types_by_slug(db: AsyncSession) -> dict[str, ServiceTypeDB]:
    result = await db.execute(select(ServiceTypeDB))
    return {service_type.slug: service_type for service_type in result.scalars().all()}


async def get_primary_contact_snapshot(
    church_repo: ChurchRepository,
    tenant_id: str,
) -> dict[str, str | None]:
    assignments = await church_repo.list_service_assignments("church", tenant_id)
    primary = pick_primary_card_assignment(assignments)
    if not primary or not primary.person:
        return {
            "contact_name": None,
            "contact_title": None,
            "contact_phone": None,
            "contact_email": None,
        }

    person = primary.person
    return {
        "contact_name": person_display_name(person) or None,
        "contact_title": assignment_title(primary),
        "contact_phone": person.phone,
        "contact_email": person.email,
    }


async def upsert_primary_card_contact(
    church_repo: ChurchRepository,
    tenant_id: str,
    *,
    name: str,
    title: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    fields: set[str] | None = None,
) -> None:
    """Create or update the primary card contact for a congregation."""
    service_types_by_slug = await load_service_types_by_slug(church_repo.db)
    assignments = await church_repo.list_service_assignments("church", tenant_id)
    primary = pick_primary_card_assignment(assignments)

    first_name, last_name = split_person_name(name)
    service_type_id, custom_service_name = resolve_service_type_for_title(
        title,
        service_types_by_slug,
    )

    if primary and primary.person:
        person = primary.person
        if fields is None or "contact_name" in fields:
            person.first_name = first_name
            person.last_name = last_name
        if fields is None or "contact_phone" in fields:
            person.phone = phone
        if fields is None or "contact_email" in fields:
            person.email = email

        update_payload: dict[str, object] = {}
        if fields is None or "contact_title" in fields:
            update_payload["serviceTypeId"] = service_type_id
            update_payload["customServiceName"] = custom_service_name

        if update_payload:
            await church_repo.update_service_assignment(
                "church",
                tenant_id,
                primary.id,
                ServiceAssignmentUpdateRequest.model_validate(update_payload),
            )
        await church_repo.db.commit()
        return

    if not service_type_id and not custom_service_name:
        custom_service_name = title or "Kontakt"

    await church_repo.create_service_assignment(
        "church",
        tenant_id,
        ServiceAssignmentCreateRequest(
            firstName=first_name,
            lastName=last_name,
            email=email,
            phone=phone,
            serviceTypeId=service_type_id,
            customServiceName=custom_service_name,
            showOnList=True,
            profileVisibility="public",
            phoneVisibility="public" if phone else "hidden",
            emailVisibility="public" if email else "hidden",
        ),
    )
