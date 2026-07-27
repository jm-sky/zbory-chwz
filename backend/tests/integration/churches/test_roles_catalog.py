"""G4 — GET /churches/roles must match ensure_acl_roles exactly, so the seed and the API
catalog can never drift apart."""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost","127.0.0.1"]')
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_POOL_SIZE", "1")
os.environ.setdefault("DATABASE_MAX_OVERFLOW", "0")

from app.core.database import Base, get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.churches.acl_models import RoleDB, RolePermissionDB
from app.modules.churches.acl_seed import ROLE_SEED, ensure_acl_roles
from main import app


@pytest_asyncio.fixture
async def ctx():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="u1@example.com", name="U1", createdAt=datetime.now(UTC))

    async with session_factory() as session:
        await ensure_acl_roles(session)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_roles_catalog_matches_ensure_acl_roles(ctx) -> None:
    client, session_factory = ctx

    response = await client.get("/api/churches/roles")
    assert response.status_code == 200
    api_roles = {r["name"]: (r["scopeType"], set(r["permissions"])) for r in response.json()}

    assert set(api_roles.keys()) == {name for name, _, _ in ROLE_SEED}

    async with session_factory() as session:
        db_result = await session.execute(select(RoleDB))
        db_roles = {r.name: r for r in db_result.scalars().all()}
        for name, scope_type, permissions in ROLE_SEED:
            role = db_roles[name]
            assert api_roles[name][0] == scope_type == role.scope_type
            perm_result = await session.execute(select(RolePermissionDB.permission).where(RolePermissionDB.role_id == role.id))
            db_perms = {row[0] for row in perm_result.all()}
            assert api_roles[name][1] == db_perms == {str(p) for p in permissions}
