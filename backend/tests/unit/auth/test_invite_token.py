"""G1 — invite tokens must be a distinct token type from password-reset tokens: a token
minted for one flow must never validate for the other, even though both are stored as a
single string field on the user and both are HS256 JWTs signed with the same secret."""

import os
from datetime import UTC, datetime, timedelta

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.modules.auth.auth_utils import create_invite_token, create_password_reset_token
from app.modules.auth.models import User


def _user(user_id: str = "u1") -> User:
    return User(id=user_id, email="u@example.com", name="User", createdAt=datetime.now(UTC))


def test_password_reset_token_does_not_validate_as_invite() -> None:
    user = _user()
    reset_token = create_password_reset_token(data={"sub": user.id})
    user.set_reset_token(reset_token, datetime.now(UTC) + timedelta(hours=1))

    # Attacker/bug scenario: the reset token ends up compared against invite_token.
    user.inviteToken = reset_token
    assert not user.is_invite_token_valid(reset_token)


def test_invite_token_does_not_validate_as_reset_token() -> None:
    user = _user()
    invite_token = create_invite_token(data={"sub": user.id})
    user.set_invite_token(
        invite_token,
        datetime.now(UTC) + timedelta(hours=168),
        invited_by=None,
        invited_at=datetime.now(UTC),
    )

    user.resetToken = invite_token
    assert not user.is_reset_token_valid(invite_token)


def test_invite_token_valid_for_matching_user_and_token() -> None:
    user = _user()
    invite_token = create_invite_token(data={"sub": user.id})
    user.set_invite_token(
        invite_token,
        datetime.now(UTC) + timedelta(hours=168),
        invited_by="inviter-1",
        invited_at=datetime.now(UTC),
    )

    assert user.is_invite_token_valid(invite_token)
    assert user.invitedBy == "inviter-1"


def test_invite_token_rejected_for_wrong_user() -> None:
    inviter_target = _user("u1")
    other_user = _user("u2")
    invite_token = create_invite_token(data={"sub": inviter_target.id})
    other_user.set_invite_token(
        invite_token,
        datetime.now(UTC) + timedelta(hours=168),
        invited_by=None,
        invited_at=datetime.now(UTC),
    )

    assert not other_user.is_invite_token_valid(invite_token)


def test_clear_invite_token_invalidates_it() -> None:
    user = _user()
    invite_token = create_invite_token(data={"sub": user.id})
    user.set_invite_token(
        invite_token,
        datetime.now(UTC) + timedelta(hours=168),
        invited_by=None,
        invited_at=datetime.now(UTC),
    )
    user.clear_invite_token()

    assert not user.is_invite_token_valid(invite_token)
