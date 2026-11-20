"""Security: 2FA enforcement in ``_verify_user_token`` must fail closed.

Regression: the 2FA check sat inside a ``try`` whose generic ``except Exception``
swallowed the 401 raised for ``tfaVerified=False`` (and any lookup error), so 2FA
was never enforced.
"""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from fastapi import HTTPException, status

from app.modules.auth.auth_utils import create_access_token
from app.modules.auth.dependencies import _verify_user_token
from app.modules.auth.models import User

LOOKUP = "app.modules.two_factor.service.TwoFactorService.has_two_factor_enabled"


def _user() -> User:
    return User(
        id="user-1",
        email="owner@example.com",
        name="Owner",
        hashedPassword="hashed",
        isActive=True,
        isEmailVerified=True,
        createdAt=datetime.now(UTC),
    )


def _deps(tfa_verified: bool) -> tuple[AsyncMock, AsyncMock, str]:
    repo = AsyncMock()
    repo.get_user_by_id.return_value = _user()
    blacklist = AsyncMock()
    blacklist.is_blacklisted.return_value = False
    blacklist.is_jti_blacklisted.return_value = False
    token = create_access_token({"sub": "user-1", "email": "owner@example.com", "tfaVerified": tfa_verified})
    return repo, blacklist, token


@pytest.mark.asyncio
async def test_unverified_token_denied_when_2fa_enabled() -> None:
    repo, blacklist, token = _deps(tfa_verified=False)
    with patch(LOOKUP, AsyncMock(return_value=True)):
        with pytest.raises(HTTPException) as exc:
            await _verify_user_token(token, repo, blacklist, AsyncMock())
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_verified_token_allowed_when_2fa_enabled() -> None:
    repo, blacklist, token = _deps(tfa_verified=True)
    with patch(LOOKUP, AsyncMock(return_value=True)):
        user = await _verify_user_token(token, repo, blacklist, AsyncMock())
    assert user.id == "user-1"


@pytest.mark.asyncio
async def test_exception_in_2fa_lookup_denies_with_503() -> None:
    repo, blacklist, token = _deps(tfa_verified=False)
    with patch(LOOKUP, AsyncMock(side_effect=RuntimeError("db down"))):
        with pytest.raises(HTTPException) as exc:
            await _verify_user_token(token, repo, blacklist, AsyncMock())
    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_allowed_when_2fa_not_enabled() -> None:
    repo, blacklist, token = _deps(tfa_verified=False)
    with patch(LOOKUP, AsyncMock(return_value=False)):
        user = await _verify_user_token(token, repo, blacklist, AsyncMock())
    assert user.id == "user-1"
