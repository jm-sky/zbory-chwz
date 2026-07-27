"""G3 — account status derivation for the people-list badge: active / invited / expired /
none, computed from raw UserDB columns (no account row => omitted, handled by the caller)."""

import os
from datetime import UTC, datetime, timedelta

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.modules.auth.db_models import UserDB
from app.modules.churches.repositories import _account_state_from_user


def _user(**overrides: object) -> UserDB:
    defaults: dict[str, object] = dict(
        id="u1",
        email="u1@example.com",
        name="U1",
        is_active=False,
        invite_token=None,
        invite_token_expiry=None,
        invited_at=None,
    )
    defaults.update(overrides)
    return UserDB(**defaults)  # type: ignore[arg-type]


def test_active_account() -> None:
    user = _user(is_active=True)
    state = _account_state_from_user(user)
    assert state.status == "active"


def test_invited_not_yet_expired() -> None:
    user = _user(invite_token="tok", invite_token_expiry=datetime.now(UTC) + timedelta(hours=1))
    state = _account_state_from_user(user)
    assert state.status == "invited"


def test_expired_invite() -> None:
    user = _user(invite_token="tok", invite_token_expiry=datetime.now(UTC) - timedelta(hours=1))
    state = _account_state_from_user(user)
    assert state.status == "expired"


def test_no_invite_outstanding() -> None:
    user = _user()
    state = _account_state_from_user(user)
    assert state.status == "none"


def test_naive_expiry_datetime_is_handled() -> None:
    """SQLite returns naive datetimes for DateTime(timezone=True) columns."""
    user = _user(invite_token="tok", invite_token_expiry=(datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None))
    state = _account_state_from_user(user)
    assert state.status == "expired"
