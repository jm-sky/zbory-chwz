"""Unit tests for 2FA login token issuance.

Regression tests for the "2FA login is functionally broken" finding
(ops-monitor review, 2026-07-20): tokens minted after a successful TOTP or
passkey verification never carried tfaVerified=True, so _verify_user_token
rejected every subsequent request from a 2FA-enabled user — enabling 2FA
locked the user out of their own account.
"""

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.auth.auth_utils import verify_token
from app.modules.two_factor.auth_utils import create_two_factor_token
from app.modules.two_factor.crypto_utils import encrypt_secret
from app.modules.two_factor.service import TwoFactorService
from app.modules.two_factor.types.repository import TwoFactorRepositoryInterface


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock(spec=TwoFactorRepositoryInterface)


@pytest.fixture
def two_factor_service(mock_repository: AsyncMock) -> TwoFactorService:
    return TwoFactorService(repository=mock_repository, challenge_store=None)


class TestVerifyTotpLogin:
    @pytest.mark.asyncio
    async def test_successful_totp_login_mints_tfa_verified_tokens(self, two_factor_service: TwoFactorService) -> None:
        two_factor_service.totp.verify_code = AsyncMock(return_value=(True, False))  # type: ignore[method-assign]
        two_factor_token = create_two_factor_token({"sub": "user-123"})

        result = await two_factor_service.verify_totp_login(two_factor_token=two_factor_token, code="123456")

        assert result["accessToken"]
        assert result["refreshToken"]

        access_payload = verify_token(result["accessToken"])
        assert access_payload["tfaVerified"] is True

        refresh_payload = verify_token(result["refreshToken"])
        assert refresh_payload["tfaVerified"] is True


class TestCompletePasskeyAuthentication:
    @pytest.mark.asyncio
    async def test_successful_passkey_login_mints_tfa_verified_tokens(self, mock_repository: AsyncMock, monkeypatch: pytest.MonkeyPatch) -> None:
        from webauthn.helpers import bytes_to_base64url

        passkey = MagicMock()
        passkey.id = "passkey-1"
        passkey.user_id = "user-123"
        passkey.is_enabled = True
        passkey.public_key = encrypt_secret(bytes_to_base64url(b"fake-public-key-bytes"))
        passkey.counter = 5

        mock_repository.get_passkey_by_credential_id = AsyncMock(return_value=passkey)
        mock_repository.update_passkey_last_used = AsyncMock()
        mock_repository.update_passkey_counter = AsyncMock()

        # Stub out the actual cryptographic verification (covered separately
        # by webauthn's own test suite) — this test is about the wiring:
        # correct passkey lookup, counter persistence, and tfaVerified tokens.
        monkeypatch.setattr(
            "app.modules.two_factor.webauthn_service.verify_authentication",
            MagicMock(return_value={"new_sign_count": 6}),
        )

        service = TwoFactorService(repository=mock_repository, challenge_store=None)
        challenge_data = {
            "user_id": "user-123",
            "challenge": base64.b64encode(b"raw-challenge-bytes").decode(),
            "challenge_type": "authentication",
        }
        credential_json = {
            "rawId": base64.b64encode(b"cred-id-bytes").decode(),
            "response": {},
        }

        result = await service.complete_passkey_authentication(
            challenge_token="unused-since-challenge_store-is-None",
            credential_json=credential_json,
            challenge_data=challenge_data,
            expected_user_id="user-123",
        )

        assert result["verified"] is True
        assert result["method"] == "webauthn"
        assert result["accessToken"]

        access_payload = verify_token(result["accessToken"])
        assert access_payload["tfaVerified"] is True

        mock_repository.update_passkey_counter.assert_awaited_once_with("passkey-1", 6)

    @pytest.mark.asyncio
    async def test_expected_user_id_mismatch_is_rejected(self, mock_repository: AsyncMock) -> None:
        service = TwoFactorService(repository=mock_repository, challenge_store=None)
        challenge_data = {
            "user_id": "user-123",
            "challenge": base64.b64encode(b"raw-challenge-bytes").decode(),
            "challenge_type": "authentication",
        }
        credential_json = {"rawId": base64.b64encode(b"cred-id-bytes").decode()}

        with pytest.raises(ValueError, match="does not belong to this user"):
            await service.complete_passkey_authentication(
                challenge_token="t",
                credential_json=credential_json,
                challenge_data=challenge_data,
                expected_user_id="someone-else",
            )
