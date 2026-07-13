"""Business logic for Phase 2/3 of the Google Contacts import.

Flow: admin picks contacts from the filtered list (Phase 1) and confirms/
corrects the church-vs-person classification -> `analyze()` fuzzy-matches
churches by name and exact-matches persons by email/phone, building a
proposal per contact -> the admin reviews/edits proposals on the mapping
screen -> `apply()` writes only the confirmed decisions to the database.

See docs/plans/2026-07-10--google-contacts-sync.md decisions #4-#7.
"""

from fastapi import Depends
from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.churches.contact_sync import upsert_primary_card_contact
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import ServiceAssignmentCreateRequest
from app.modules.churches.slug_utils import slugify
from app.modules.congregations.geo import DEFAULT_COUNTRY, is_valid_province
from app.modules.congregations.repositories import CongregationRepository
from app.modules.google_contacts.repositories import GoogleContactsRepository
from app.modules.google_contacts.schemas import (
    GoogleContactChurchApplyItem,
    GoogleContactChurchProposal,
    GoogleContactImportSelection,
    GoogleContactPersonApplyItem,
    GoogleContactPersonProposal,
    GoogleContactsAnalyzeRequest,
    GoogleContactsAnalyzeResponse,
    GoogleContactsApplyRequest,
    GoogleContactsApplyResponse,
    GoogleContactsCandidateTenant,
    GoogleContactsServiceType,
    GoogleContactSuggestion,
)
from app.modules.tenants.db_models import TenantDB
from app.modules.tenants.repositories import TenantRepository

# Below this rapidfuzz score (0-100), a name is treated as having no match
# rather than risking a wrong auto-match (same threshold as the AI-assisted
# congregation address import — see congregations/import_service.py).
_MATCH_THRESHOLD = 80.0


class GoogleContactsImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant_repo = TenantRepository(db)
        self._congregation_repo = CongregationRepository(db)
        self._church_repo = ChurchRepository(db)
        self._google_contacts_repo = GoogleContactsRepository(db)

    async def analyze(self, request: GoogleContactsAnalyzeRequest) -> GoogleContactsAnalyzeResponse:
        tenants = await self._tenant_repo.list_all()
        name_slugs = {t.id: slugify(t.name) for t in tenants}
        service_types = await self._church_repo.list_service_types()

        church_proposals: list[GoogleContactChurchProposal] = []
        person_proposals: list[GoogleContactPersonProposal] = []

        for selection in request.items:
            if selection.type == "church":
                church_proposals.append(await self._build_church_proposal(selection.contact, tenants, name_slugs))
            else:
                person_proposals.append(await self._build_person_proposal(selection.contact))

        return GoogleContactsAnalyzeResponse(
            churchProposals=church_proposals,
            personProposals=person_proposals,
            candidateTenants=[GoogleContactsCandidateTenant(tenantId=t.id, name=t.name) for t in tenants],
            serviceTypes=[GoogleContactsServiceType(id=st.id, name=st.name) for st in service_types],
        )

    async def _build_church_proposal(
        self,
        contact: GoogleContactSuggestion,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> GoogleContactChurchProposal:
        detected_name = contact.organizationName or contact.displayName or contact.resourceName
        tenant_id, matched_name, confidence = self._match_tenant(detected_name, tenants, name_slugs)
        match_type = "matched" if tenant_id else "new"

        province = contact.addressProvince
        country = contact.addressCountry or DEFAULT_COUNTRY
        if not is_valid_province(country, province):
            province = None

        return GoogleContactChurchProposal(
            resourceName=contact.resourceName,
            matchType=match_type,  # type: ignore[arg-type]
            tenantId=tenant_id,
            matchedName=matched_name,
            confidence=round(confidence, 1),
            name=detected_name,
            street=contact.addressStreet,
            city=contact.addressCity,
            postalCode=contact.addressPostalCode,
            province=province,
            country=country,
            phone=contact.phoneNumbers[0] if contact.phoneNumbers else None,
            email=contact.emailAddresses[0] if contact.emailAddresses else None,
        )

    def _match_tenant(
        self,
        detected_name: str,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> tuple[str | None, str | None, float]:
        if not name_slugs:
            return None, None, 0.0

        match = process.extractOne(slugify(detected_name), name_slugs, scorer=fuzz.WRatio)
        if match is None:
            return None, None, 0.0

        _, score, matched_tenant_id = match
        if score < _MATCH_THRESHOLD:
            return None, None, score

        matched_name = next(t.name for t in tenants if t.id == matched_tenant_id)
        return matched_tenant_id, matched_name, score

    async def _build_person_proposal(self, contact: GoogleContactSuggestion) -> GoogleContactPersonProposal:
        email = contact.emailAddresses[0] if contact.emailAddresses else None
        phone = contact.phoneNumbers[0] if contact.phoneNumbers else None

        match = await self._church_repo.find_person_by_email_or_phone(email=email, phone=phone)
        if match:
            person, matched_by = match
            matched_name = " ".join(p for p in (person.first_name, person.last_name) if p) or person.email or person.phone
            return GoogleContactPersonProposal(
                resourceName=contact.resourceName,
                matchType="matched",
                personId=person.id,
                matchedName=matched_name,
                matchedBy=matched_by,  # type: ignore[arg-type]
                firstName=contact.firstName,
                lastName=contact.lastName,
                email=email,
                phone=phone,
            )

        return GoogleContactPersonProposal(
            resourceName=contact.resourceName,
            matchType="new",
            firstName=contact.firstName,
            lastName=contact.lastName,
            email=email,
            phone=phone,
        )

    async def apply(self, request: GoogleContactsApplyRequest, *, user_id: str) -> GoogleContactsApplyResponse:
        churches_created = churches_updated = 0
        persons_created = persons_updated = 0
        skipped = 0

        for item in request.churchItems:
            if item.action == "skip":
                skipped += 1
                await self._log(user_id, item.resourceName, "church", None, "skipped")
                continue

            tenant_id = await self._apply_church_item(item, owner_user_id=user_id)
            if item.action == "create":
                churches_created += 1
            else:
                churches_updated += 1
            await self._log(user_id, item.resourceName, "church", tenant_id, "created" if item.action == "create" else "updated")

        for person_item in request.personItems:
            if person_item.action == "skip":
                skipped += 1
                await self._log(user_id, person_item.resourceName, "person", None, "skipped")
                continue

            person_id = await self._apply_person_item(person_item)
            if person_item.action == "create":
                persons_created += 1
            else:
                persons_updated += 1
            await self._log(user_id, person_item.resourceName, "person", person_id, "created" if person_item.action == "create" else "updated")

        return GoogleContactsApplyResponse(
            churchesCreated=churches_created,
            churchesUpdated=churches_updated,
            personsCreated=persons_created,
            personsUpdated=persons_updated,
            skipped=skipped,
        )

    async def _log(self, user_id: str, resource_name: str, entity_type: str, matched_entity_id: str | None, action: str) -> None:
        await self._google_contacts_repo.log_import(
            user_id=user_id,
            google_resource_name=resource_name,
            entity_type=entity_type,
            matched_entity_id=matched_entity_id,
            action=action,
        )

    async def _apply_church_item(self, item: GoogleContactChurchApplyItem, *, owner_user_id: str) -> str:
        if item.action == "create":
            assert item.name is not None
            tenant, _ = await self._tenant_repo.create_tenant(
                name=item.name,
                description=None,
                owner_user_id=owner_user_id,
                status="draft",
            )
            await provision_church_for_tenant(self.db, tenant)
            await self.db.commit()
            tenant_id = tenant.id
        else:
            assert item.tenantId is not None
            tenant_id = item.tenantId
            if item.name:
                existing_tenant = await self._get_tenant(tenant_id)
                if existing_tenant:
                    existing_tenant.name = item.name
                    await self.db.commit()

        if item.city:
            await self._apply_church_address(tenant_id, item)
        if item.phone or item.email:
            await self._apply_church_contact(tenant_id, item)

        return tenant_id

    async def _get_tenant(self, tenant_id: str) -> TenantDB | None:
        for tenant in await self._tenant_repo.list_all():
            if tenant.id == tenant_id:
                return tenant
        return None

    async def _apply_church_address(self, tenant_id: str, item: GoogleContactChurchApplyItem) -> None:
        existing = await self._congregation_repo.get_address_by_tenant_id(tenant_id)
        assert item.city is not None
        await self._congregation_repo.create_or_update_address(
            tenant_id,
            street=item.street,
            city=item.city,
            postal_code=item.postalCode,
            province=item.province,
            country=item.country or DEFAULT_COUNTRY,
            status=existing.status if existing else "draft",
        )

    async def _apply_church_contact(self, tenant_id: str, item: GoogleContactChurchApplyItem) -> None:
        name = item.name
        if not name:
            existing_tenant = await self._get_tenant(tenant_id)
            name = existing_tenant.name if existing_tenant else None
        if not name:
            return

        await upsert_primary_card_contact(
            self._church_repo,
            tenant_id,
            name=name,
            phone=item.phone,
            email=item.email,
        )

    async def _apply_person_item(self, item: GoogleContactPersonApplyItem) -> str:
        if item.assignToChurch:
            assert item.churchId is not None
            assignment = await self._church_repo.create_service_assignment(
                "church",
                item.churchId,
                ServiceAssignmentCreateRequest(
                    personId=item.personId,
                    firstName=item.firstName,
                    lastName=item.lastName,
                    email=item.email,
                    phone=item.phone,
                    serviceTypeId=item.serviceTypeId,
                    customServiceName=item.customServiceName,
                ),
            )
            return assignment.person_id

        if item.personId:
            person = await self._church_repo.get_person(item.personId)
            if person:
                if item.firstName is not None:
                    person.first_name = item.firstName
                if item.lastName is not None:
                    person.last_name = item.lastName
                if item.email is not None:
                    person.email = item.email
                if item.phone is not None:
                    person.phone = item.phone
                await self.db.commit()
                return person.id

        return await self._church_repo.create_standalone_person(
            first_name=item.firstName,
            last_name=item.lastName,
            email=item.email,
            phone=item.phone,
        )


def get_google_contacts_import_service(
    db: AsyncSession = Depends(get_db),
) -> GoogleContactsImportService:
    return GoogleContactsImportService(db)
