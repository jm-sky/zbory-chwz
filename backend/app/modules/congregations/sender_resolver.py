"""Resolves an inbound clergy e-mail sender to a known contact and decides
which congregation (tenant) they're authorized to propose updates for.

Deliberately independent of `churches.acl_service.AclService`: that service
answers "can this logged-in *platform user* administer this church", keyed by
`UserRoleAssignmentDB.user_id`. A pastor/bishop/deacon does not necessarily
have a platform account (account creation is opt-in, see
`churches.repositories.ChurchRepository._maybe_create_user_and_acl`), so
e-mail sender authorization is resolved directly from the public contact
directory (`PersonDB.email` + `ServiceAssignmentDB`) instead, using the same
church/region/community scope hierarchy.

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.crypto.encrypted_types import hmac_email
from app.modules.churches.db_models import ChurchDB, PersonDB, ServiceAssignmentDB
from app.modules.congregations.tenant_matching import match_tenant_by_name
from app.modules.tenants.db_models import TenantDB

SenderResolutionKind = Literal[
    "own_church",  # no name/city in the e-mail; sender has exactly one church-scope assignment
    "matched_by_name",  # name/city resolved a tenant, and the sender is authorized for it
    "unauthorized",  # name/city resolved a tenant, but the sender has no scope covering it
    "unknown_sender",  # sender e-mail matches no known Person
    "ambiguous",  # sender known, but no single target tenant could be determined
]


@dataclass
class SenderResolution:
    person: PersonDB | None
    tenant_id: str | None
    kind: SenderResolutionKind


class SenderResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(
        self,
        sender_email: str,
        detected_name_or_city: str | None,
        tenants: list[TenantDB],
        name_slugs: dict[str, str],
    ) -> SenderResolution:
        person = await self._find_person(sender_email)
        if person is None:
            return SenderResolution(None, None, "unknown_sender")

        if not detected_name_or_city:
            tenant_id = await self._own_church_tenant(person)
            if tenant_id is None:
                return SenderResolution(person, None, "ambiguous")
            return SenderResolution(person, tenant_id, "own_church")

        tenant_id, _matched_name, _confidence = match_tenant_by_name(detected_name_or_city, tenants, name_slugs)
        if tenant_id is None:
            return SenderResolution(person, None, "ambiguous")

        if await self.is_authorized(person, tenant_id):
            return SenderResolution(person, tenant_id, "matched_by_name")
        return SenderResolution(person, tenant_id, "unauthorized")

    async def is_authorized(self, person: PersonDB, tenant_id: str) -> bool:
        church = await self._church_for_tenant(tenant_id)
        if church is None:
            return False

        for assignment in await self._assignments_for_person(person.id):
            if assignment.scope_type == "church" and assignment.scope_id == tenant_id:
                return True
            if assignment.scope_type == "region" and church.region_id and assignment.scope_id == church.region_id:
                return True
            if assignment.scope_type == "community" and assignment.scope_id == church.community_id:
                return True
        return False

    async def _own_church_tenant(self, person: PersonDB) -> str | None:
        """The tenant of the sender's own congregation, i.e. the single
        church-scope assignment they hold. Scope_id for scope_type="church"
        is the tenant_id (see churches.repositories.list_service_assignments
        call sites), not the church_id."""
        church_assignments = [a for a in await self._assignments_for_person(person.id) if a.scope_type == "church"]
        if len(church_assignments) != 1:
            return None
        return church_assignments[0].scope_id

    async def _find_person(self, email: str) -> PersonDB | None:
        # PersonDB.email is encrypted at rest (EncryptedString), so an exact
        # match has to go through the HMAC blind index rather than comparing
        # (or lower()-ing) the column directly — see
        # app/common/crypto/encrypted_types.hmac_email.
        result = await self.db.execute(select(PersonDB).where(PersonDB.email_bidx == hmac_email(email)))
        return result.scalars().first()

    async def _assignments_for_person(self, person_id: str) -> list[ServiceAssignmentDB]:
        result = await self.db.execute(select(ServiceAssignmentDB).where(ServiceAssignmentDB.person_id == person_id))
        return list(result.scalars().all())

    async def _church_for_tenant(self, tenant_id: str) -> ChurchDB | None:
        # ChurchDB.id == tenant_id by construction (see
        # churches.provisioning.provision_church_for_tenant) — ChurchDB.tenant_id
        # is a different thing entirely (the shared CHWZ org tenant), not this
        # congregation's own tenant.
        result = await self.db.execute(select(ChurchDB).where(ChurchDB.id == tenant_id))
        return result.scalars().first()
