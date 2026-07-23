"""Repository layer for Google Contacts connections."""

from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.google_contacts.db_models import (
    GoogleContactsConnectionDB,
    GoogleContactsImportLogDB,
)


class GoogleContactsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_connection(self, user_id: str) -> GoogleContactsConnectionDB | None:
        result = await self.db.execute(
            select(GoogleContactsConnectionDB).where(
                GoogleContactsConnectionDB.user_id == user_id,
                GoogleContactsConnectionDB.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def upsert_connection(
        self,
        *,
        user_id: str,
        scope: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> GoogleContactsConnectionDB:
        existing = await self.get_active_connection(user_id)

        if existing:
            existing.scope = scope
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            existing.expires_at = expires_at
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        connection = GoogleContactsConnectionDB(
            id=generate_id(),
            user_id=user_id,
            scope=scope,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        self.db.add(connection)
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def update_tokens(
        self,
        connection: GoogleContactsConnectionDB,
        *,
        access_token: str,
        expires_at: datetime | None,
    ) -> GoogleContactsConnectionDB:
        connection.access_token = access_token
        connection.expires_at = expires_at
        await self.db.commit()
        await self.db.refresh(connection)
        return connection

    async def revoke_connection(self, user_id: str) -> bool:
        connection = await self.get_active_connection(user_id)
        if not connection:
            return False
        connection.revoked_at = datetime.now(UTC)
        await self.db.commit()
        return True

    async def log_import(
        self,
        *,
        user_id: str,
        google_resource_name: str,
        entity_type: str,
        matched_entity_id: str | None,
        action: str,
    ) -> None:
        self.db.add(
            GoogleContactsImportLogDB(
                id=generate_id(),
                user_id=user_id,
                google_resource_name=google_resource_name,
                entity_type=entity_type,
                matched_entity_id=matched_entity_id,
                action=action,
            )
        )
        await self.db.commit()


def get_google_contacts_repository(
    db: AsyncSession = Depends(get_db),
) -> GoogleContactsRepository:
    return GoogleContactsRepository(db)
