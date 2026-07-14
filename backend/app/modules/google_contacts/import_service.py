"""Business logic for Phase 2/3 of the Google Contacts import.

Flow: admin picks contacts from the filtered list (Phase 1) and confirms/
corrects the church-vs-person classification -> `analyze()` fuzzy-matches
churches by name and exact-matches persons by email/phone, building a
proposal per contact -> the admin reviews/edits proposals on the mapping
screen -> `apply()` writes only the confirmed decisions to the database.

See docs/plans/2026-07-10--google-contacts-sync.md decisions #4-#7.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.churches.contact_sync import get_primary_contact_snapshot, upsert_primary_card_contact
from app.modules.churches.provisioning import provision_church_for_tenant
from app.modules.churches.repositories import ChurchRepository
from app.modules.churches.schemas import ServiceAssignmentCreateRequest
from app.modules.congregations.field_diff import FIELD_LABELS as _CONGREGATION_FIELD_LABELS
from app.modules.congregations.field_diff import normalize_phone
from app.modules.congregations.geo import DEFAULT_COUNTRY, is_valid_province
from app.modules.congregations.repositories import CongregationRepository
from app.modules.congregations.tenant_matching import match_slug, match_tenant_by_name
from app.modules.google_contacts.repositories import GoogleContactsRepository
from app.modules.google_contacts.schemas import (
    GoogleContactChurchApplyItem,
    GoogleContactChurchProposal,
    GoogleContactFieldChange,
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

# Church proposal field keys -> (congregations.field_diff key to reuse the
# label from, display group). Reusing the shared labels keeps this module's
# diff in sync with the AI-text and e-mail importers instead of maintaining
# a second copy of the Polish field names.
_CHURCH_FIELD_KEYS: dict[str, tuple[str, str]] = {
    "street": ("street", "address"),
    "city": ("city", "address"),
    "postalCode": ("postal_code", "address"),
    "province": ("province", "address"),
    "country": ("country", "address"),
    "phone": ("contact_phone", "contact"),
    "email": ("contact_email", "contact"),
}

_PERSON_FIELD_LABELS: dict[str, str] = {
    "firstName": "Imię",
    "lastName": "Nazwisko",
    "email": "E-mail",
    "phone": "Telefon",
}

_ADDRESS_ITEM_FIELDS = {"street", "city", "postalCode", "province", "country"}
_CONTACT_ITEM_FIELDS = {"phone", "email"}


def _build_field_changes(
    new_values: dict[str, str | None],
    old_values: dict[str, str | None],
    labels: dict[str, str],
    groups: dict[str, str],
    *,
    show_all: bool,
) -> list[GoogleContactFieldChange]:
    keys = new_values if show_all else {key: value for key, value in new_values.items() if value is not None and value != old_values[key]}
    return [
        GoogleContactFieldChange(
            field=key,
            label=labels[key],
            group=groups[key],  # type: ignore[arg-type]
            oldValue=old_values[key],
            newValue=new_values[key],
        )
        for key in keys
    ]


class GoogleContactsImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant_repo = TenantRepository(db)
        self._congregation_repo = CongregationRepository(db)
        self._church_repo = ChurchRepository(db)
        self._google_contacts_repo = GoogleContactsRepository(db)

    async def analyze(self, request: GoogleContactsAnalyzeRequest) -> GoogleContactsAnalyzeResponse:
        tenants = await self._tenant_repo.list_all()
        name_slugs = {t.id: match_slug(t.name) for t in tenants}
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
        tenant_id, matched_name, confidence = match_tenant_by_name(detected_name, tenants, name_slugs)
        match_type = "matched" if tenant_id else "new"

        province = contact.addressProvince
        country = contact.addressCountry or DEFAULT_COUNTRY
        if not is_valid_province(country, province):
            province = None

        new_values: dict[str, str | None] = {
            "street": contact.addressStreet,
            "city": contact.addressCity,
            "postalCode": contact.addressPostalCode,
            "province": province,
            "country": country,
            "phone": normalize_phone(contact.phoneNumbers[0]) if contact.phoneNumbers else None,
            "email": contact.emailAddresses[0] if contact.emailAddresses else None,
        }
        old_values = await self._church_old_values(tenant_id)
        labels = {key: _CONGREGATION_FIELD_LABELS[label_key] for key, (label_key, _group) in _CHURCH_FIELD_KEYS.items()}
        groups = {key: group for key, (_label_key, group) in _CHURCH_FIELD_KEYS.items()}
        fields = _build_field_changes(new_values, old_values, labels, groups, show_all=match_type == "new")

        return GoogleContactChurchProposal(
            resourceName=contact.resourceName,
            matchType=match_type,  # type: ignore[arg-type]
            tenantId=tenant_id,
            matchedName=matched_name,
            confidence=round(confidence, 1),
            name=detected_name,
            street=new_values["street"],
            city=new_values["city"],
            postalCode=new_values["postalCode"],
            province=new_values["province"],
            country=new_values["country"],
            phone=new_values["phone"],
            email=new_values["email"],
            fields=fields,
        )

    async def _church_old_values(self, tenant_id: str | None) -> dict[str, str | None]:
        if not tenant_id:
            return dict.fromkeys(_CHURCH_FIELD_KEYS, None)

        address = await self._congregation_repo.get_address_by_tenant_id(tenant_id)
        contact = await get_primary_contact_snapshot(self._church_repo, tenant_id)
        return {
            "street": address.street if address else None,
            "city": address.city if address else None,
            "postalCode": address.postal_code if address else None,
            "province": address.province if address else None,
            "country": address.country if address else None,
            "phone": normalize_phone(contact["contact_phone"]),
            "email": contact["contact_email"],
        }

    async def _build_person_proposal(self, contact: GoogleContactSuggestion) -> GoogleContactPersonProposal:
        email = contact.emailAddresses[0] if contact.emailAddresses else None
        phone = contact.phoneNumbers[0] if contact.phoneNumbers else None
        new_values: dict[str, str | None] = {
            "firstName": contact.firstName,
            "lastName": contact.lastName,
            "email": email,
            "phone": phone,
        }
        groups = dict.fromkeys(_PERSON_FIELD_LABELS, "contact")

        match = await self._church_repo.find_person_by_email_or_phone(email=email, phone=phone)
        if match:
            person, matched_by = match
            matched_name = " ".join(p for p in (person.first_name, person.last_name) if p) or person.email or person.phone
            old_values = {
                "firstName": person.first_name,
                "lastName": person.last_name,
                "email": person.email,
                "phone": person.phone,
            }
            return GoogleContactPersonProposal(
                resourceName=contact.resourceName,
                matchType="matched",
                personId=person.id,
                matchedName=matched_name,
                matchedBy=matched_by,  # type: ignore[arg-type]
                firstName=new_values["firstName"],
                lastName=new_values["lastName"],
                email=new_values["email"],
                phone=new_values["phone"],
                fields=_build_field_changes(new_values, old_values, _PERSON_FIELD_LABELS, groups, show_all=True),
            )

        old_values = dict.fromkeys(_PERSON_FIELD_LABELS, None)
        return GoogleContactPersonProposal(
            resourceName=contact.resourceName,
            matchType="new",
            firstName=new_values["firstName"],
            lastName=new_values["lastName"],
            email=new_values["email"],
            phone=new_values["phone"],
            fields=_build_field_changes(new_values, old_values, _PERSON_FIELD_LABELS, groups, show_all=True),
        )

    async def apply(self, request: GoogleContactsApplyRequest, *, user_id: str) -> GoogleContactsApplyResponse:
        churches_created = churches_updated = 0
        persons_created = persons_updated = 0
        skipped = 0
        resource_name_to_tenant_id: dict[str, str] = {}

        for item in request.churchItems:
            if item.action == "skip":
                skipped += 1
                await self._log(user_id, item.resourceName, "church", None, "skipped")
                continue

            tenant_id = await self._apply_church_item(item, owner_user_id=user_id)
            resource_name_to_tenant_id[item.resourceName] = tenant_id
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

            person_id = await self._apply_person_item(person_item, resource_name_to_tenant_id)
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
        provided = item.model_fields_set

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

        if provided & _ADDRESS_ITEM_FIELDS:
            await self._apply_church_address(tenant_id, item, provided)
        if provided & _CONTACT_ITEM_FIELDS:
            await self._apply_church_contact(tenant_id, item, provided)

        return tenant_id

    async def _get_tenant(self, tenant_id: str) -> TenantDB | None:
        for tenant in await self._tenant_repo.list_all():
            if tenant.id == tenant_id:
                return tenant
        return None

    async def _apply_church_address(self, tenant_id: str, item: GoogleContactChurchApplyItem, provided: set[str]) -> None:
        # Only overwrite the fields the admin actually checked to apply -
        # `create_or_update_address` replaces the whole row, so anything not
        # in `provided` must be filled in from the existing row instead of
        # being wiped to null.
        existing = await self._congregation_repo.get_address_by_tenant_id(tenant_id)

        def merged(key: str, new_value: str | None, existing_value: str | None) -> str | None:
            return new_value if key in provided else existing_value

        city = merged("city", item.city, existing.city if existing else None)
        if not city:
            return

        await self._congregation_repo.create_or_update_address(
            tenant_id,
            street=merged("street", item.street, existing.street if existing else None),
            city=city,
            postal_code=merged("postalCode", item.postalCode, existing.postal_code if existing else None),
            province=merged("province", item.province, existing.province if existing else None),
            country=merged("country", item.country, existing.country if existing else None) or DEFAULT_COUNTRY,
            status=existing.status if existing else "draft",
        )

    async def _apply_church_contact(self, tenant_id: str, item: GoogleContactChurchApplyItem, provided: set[str]) -> None:
        name = item.name
        if not name:
            existing_tenant = await self._get_tenant(tenant_id)
            name = existing_tenant.name if existing_tenant else None
        if not name:
            return

        # Name/title always sync to the church name (existing behavior);
        # phone/email only get touched if the admin checked them, so an
        # unchecked field isn't wiped to null.
        fields = {"contact_name", "contact_title"}
        if "phone" in provided:
            fields.add("contact_phone")
        if "email" in provided:
            fields.add("contact_email")

        await upsert_primary_card_contact(
            self._church_repo,
            tenant_id,
            name=name,
            phone=item.phone,
            email=item.email,
            fields=fields,
        )

    async def _apply_person_item(self, item: GoogleContactPersonApplyItem, resource_name_to_tenant_id: dict[str, str]) -> str:
        if item.assignToChurch:
            church_id = item.churchId
            if not church_id and item.newChurchResourceName:
                church_id = resource_name_to_tenant_id.get(item.newChurchResourceName)
                if not church_id:
                    raise ValueError(f"Cannot assign person '{item.resourceName}' to church " f"'{item.newChurchResourceName}': that church was skipped or not found in this batch")
            assert church_id is not None
            assignment = await self._church_repo.create_service_assignment(
                "church",
                church_id,
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
