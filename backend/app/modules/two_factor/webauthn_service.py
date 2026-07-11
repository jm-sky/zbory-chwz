"""WebAuthn/Passkey service layer for registration and authentication.

This service handles all WebAuthn-related operations including:
- Passkey registration and verification
- Passkey authentication
- Passkey management (delete, list, status)

Uses composition pattern - no inheritance.
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt

from app.core.config import settings

from .crypto_utils import encrypt_secret
from .exceptions import SetupTokenError
from .types.jwt import PasskeyRegistrationTokenPayload
from .types.repository import TwoFactorRepositoryInterface
from .webauthn_utils import create_registration_options, verify_registration

logger = logging.getLogger(__name__)


def _create_passkey_registration_token(user_id: str, challenge: str) -> str:
    """Create a short-lived JWT for passkey registration.

    Args:
        user_id: User ID
        challenge: WebAuthn challenge

    Returns:
        JWT token string
    """
    expires = datetime.now(UTC) + timedelta(minutes=10)
    payload: dict[str, Any] = {
        "sub": user_id,
        "challenge": challenge,
        "type": "passkey_registration",
        "exp": int(expires.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.security.secret_key,
        algorithm=settings.security.jwt_algorithm,
    )


def _verify_passkey_registration_token(
    token: str,
) -> PasskeyRegistrationTokenPayload:
    """Verify and decode passkey registration token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload

    Raises:
        SetupTokenError: If token is invalid or expired
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.security.secret_key,
            algorithms=[settings.security.jwt_algorithm],
        )
        if payload.get("type") != "passkey_registration":
            raise SetupTokenError("Invalid token type for passkey registration")
        if "challenge" not in payload:
            raise SetupTokenError("Invalid token - missing challenge")
        return cast(PasskeyRegistrationTokenPayload, payload)
    except jwt.ExpiredSignatureError as exc:
        raise SetupTokenError("Registration token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise SetupTokenError("Invalid registration token") from exc


class WebAuthnService:
    """Service for WebAuthn/Passkey operations using composition pattern."""

    def __init__(self, repository: TwoFactorRepositoryInterface, challenge_store: Any = None):
        """Initialize with repository dependency.

        Args:
            repository: Two-factor repository interface
            challenge_store: WebAuthn challenge store (optional, imported to avoid circular dependency)
        """
        self.repository = repository
        self.challenge_store = challenge_store

    async def initiate_registration(
        self,
        user_id: str,
        user_email: str,
        user_name: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Initiate passkey registration by generating WebAuthn options.

        Args:
            user_id: User ID
            user_email: User email
            user_name: User display name
            name: Passkey name (optional, will be generated if not provided)

        Returns:
            Dict with options, registrationToken, expiresAt
        """
        # Generate registration options and challenge
        options_json, challenge = create_registration_options(user_id, user_email, user_name)

        # Create registration token
        registration_token = _create_passkey_registration_token(user_id, challenge)

        # Get expiration (10 minutes)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        return {
            "options": options_json,
            "registrationToken": registration_token,
            "expiresAt": expires_at,
        }

    async def complete_registration(
        self,
        registration_token: str,
        credential_json: dict[str, Any],
        name: str | None = None,
        user_agent: str | None = None,
        origin: str | None = None,
    ) -> dict[str, Any]:
        """Complete passkey registration by verifying credential and saving.

        Args:
            registration_token: JWT registration token
            credential_json: PublicKeyCredential from WebAuthn API
            name: Passkey name (optional)
            user_agent: User agent string for device detection
            origin: Expected origin (optional, uses settings default)

        Returns:
            Dict with passkey details

        Raises:
            SetupTokenError: If token invalid
            ValueError: If verification fails
        """
        # Verify registration token
        payload = _verify_passkey_registration_token(registration_token)
        user_id: str = payload["sub"]
        expected_challenge: str = payload["challenge"]

        # Get origin from settings if not provided
        if not origin:
            origin = getattr(
                getattr(settings, "two_factor", object()),
                "webauthn_origin",
                "http://localhost:3000",
            )

        # Verify WebAuthn credential
        verified_data = verify_registration(
            credential_json=credential_json,
            expected_challenge=expected_challenge,
            expected_origin=origin,
        )

        # Encrypt public key
        encrypted_public_key = encrypt_secret(verified_data["public_key"])

        # Generate name if not provided
        if not name:
            name = self._generate_passkey_name(user_agent)

        # Save transports as JSON
        transports_json = json.dumps(verified_data.get("transports", [])) if verified_data.get("transports") else None

        # Create passkey in database
        passkey_id = await self.repository.create_passkey(
            user_id=user_id,
            name=name,
            credential_id=verified_data["credential_id"],
            encrypted_public_key=encrypted_public_key,
            counter=verified_data["counter"],
            aaguid=verified_data.get("aaguid"),
            transports_json=transports_json,
            backup_eligible=verified_data.get("backup_eligible", False),
            backup_state=verified_data.get("backup_state", False),
            user_agent=user_agent,
        )

        # Get created passkey
        passkeys = await self.repository.get_passkeys(user_id)
        created_passkey = next((pk for pk in passkeys if pk.id == passkey_id), None)

        if not created_passkey:
            raise ValueError("Failed to retrieve created passkey")

        # Convert to response format
        return self._passkey_to_dict(created_passkey)

    async def initiate_authentication(self, user_id: str) -> dict[str, Any]:
        """Initiate passkey authentication for user.

        Args:
            user_id: User ID attempting to authenticate

        Returns:
            Dict with authentication options, challengeToken, expiresAt,
            and _challenge_data (temp solution)

        Raises:
            ValueError: If user has no passkeys registered
        """
        # Get user's passkeys
        passkeys = await self.repository.get_passkeys(user_id)

        if not passkeys:
            raise ValueError("No passkeys registered for this user")

        # Generate challenge
        challenge = secrets.token_urlsafe(32)

        # Create credential IDs list
        allow_credentials = []
        for pk in passkeys:
            if pk.is_enabled:
                credential_id_bytes = base64.b64decode(pk.credential_id)
                transports = json.loads(pk.transports) if pk.transports else []

                allow_credentials.append(
                    {
                        "id": base64.b64encode(credential_id_bytes).decode(),
                        "type": "public-key",
                        "transports": transports,
                    }
                )

        # Create challenge token
        challenge_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)

        # Store challenge in Redis (PRODUCTION SAFE)
        if self.challenge_store:
            await self.challenge_store.store_challenge(
                challenge_token=challenge_token,
                user_id=user_id,
                challenge=challenge.encode("utf-8"),
                challenge_type="authentication",
                ttl=300,  # 5 minutes
            )
            logger.info(f"Challenge stored in Redis for user_id={user_id}")
        else:
            logger.warning("Challenge store not available - challenge NOT stored server-side (INSECURE)")

        # Create authentication options
        # Get domain from frontend URL or default to localhost
        frontend_url = settings.frontend_url
        # Extract domain from URL (e.g., "http://localhost:3000" -> "localhost")
        from urllib.parse import urlparse

        parsed = urlparse(frontend_url)
        rp_id = parsed.hostname or "localhost"

        options = {
            "challenge": challenge,
            "timeout": 300000,  # 5 minutes in milliseconds
            "rpId": rp_id,
            "allowCredentials": allow_credentials,
            "userVerification": "required",
        }

        return {
            "options": options,
            "challengeToken": challenge_token,
            "expiresAt": expires_at,
        }

    async def complete_authentication(
        self,
        challenge_token: str,
        credential_json: dict,
        challenge_data: dict | None = None,
    ) -> dict[str, Any]:
        """Complete passkey authentication verification.

        Args:
            challenge_token: Challenge token from initiation
            credential_json: PublicKeyCredential from WebAuthn API
            challenge_data: Challenge data (deprecated - use Redis)

        Returns:
            Dict with success, userId, passkeyId

        Raises:
            ValueError: If verification fails
        """
        # Retrieve challenge_data from Redis using challenge_token
        if self.challenge_store:
            challenge_data_from_redis = await self.challenge_store.get_and_delete_challenge(challenge_token)
            if not challenge_data_from_redis:
                raise ValueError("Challenge not found or expired")
            challenge_data = challenge_data_from_redis
            logger.info("Challenge retrieved and consumed from Redis")
        elif not challenge_data:
            raise ValueError("Challenge data not found or expired - Redis not configured")

        # Verify challenge type
        if challenge_data.get("challenge_type") != "authentication":
            raise ValueError("Invalid challenge type")

        # Get credential ID from response
        raw_id = credential_json.get("rawId")
        if not raw_id:
            raise ValueError("Missing credential rawId")

        # Decode credential ID
        credential_id = base64.b64decode(raw_id)
        credential_id_b64 = base64.b64encode(credential_id).decode()

        # Find passkey by credential ID
        passkey = await self.repository.get_passkey_by_credential_id(credential_id_b64)

        if not passkey:
            raise ValueError("Passkey not found")

        if not passkey.is_enabled:
            raise ValueError("Passkey is disabled")

        # Verify passkey belongs to the user
        if passkey.user_id != challenge_data["user_id"]:
            raise ValueError("Passkey does not belong to user")

        # TODO: Full WebAuthn verification using webauthn library
        # For now, basic check (implement full verification in production)

        # Update passkey usage
        await self.repository.update_passkey_last_used(passkey.id)

        # Extract and update counter from authenticator data
        response = credential_json.get("response", {})
        authenticator_data = response.get("authenticatorData")
        if authenticator_data:
            auth_data_bytes = base64.b64decode(authenticator_data)
            if len(auth_data_bytes) >= 37:
                # Counter is at bytes 33-37
                counter = int.from_bytes(auth_data_bytes[33:37], "big")
                await self.repository.update_passkey_counter(passkey.id, counter)

        return {
            "success": True,
            "userId": passkey.user_id,
            "passkeyId": passkey.id,
        }

    async def get_status(self, user_id: str) -> dict[str, Any]:
        """Get WebAuthn/Passkey status for user.

        Args:
            user_id: User ID

        Returns:
            Dict with enabled, passkeys list
        """
        passkeys = await self.repository.get_passkeys(user_id)

        passkey_list = [self._passkey_to_dict(pk) for pk in passkeys]

        return {
            "enabled": len(passkeys) > 0,
            "passkeys": passkey_list,
        }

    async def delete_passkey(self, passkey_id: str, user_id: str) -> None:
        """Delete a passkey for a user.

        Args:
            passkey_id: ID of the passkey to delete
            user_id: ID of the user who owns the passkey

        Raises:
            ValueError: If passkey not found or doesn't belong to user
        """
        # Verify passkey belongs to user before deleting
        passkeys = await self.repository.get_passkeys(user_id)
        passkey_exists = any(pk.id == passkey_id for pk in passkeys)

        if not passkey_exists:
            raise ValueError("Passkey not found or does not belong to user")

        await self.repository.delete_passkey(passkey_id)

    def _generate_passkey_name(self, user_agent: str | None) -> str:
        """Generate passkey name from user agent.

        Args:
            user_agent: User agent string

        Returns:
            Generated passkey name
        """
        if not user_agent:
            return "Security Key"

        # Simple extraction (could be improved with user_agents library)
        if "iPhone" in user_agent or "iPad" in user_agent:
            return "iPhone/iPad"
        elif "Mac" in user_agent:
            return "Mac"
        elif "Windows" in user_agent:
            return "Windows Device"
        elif "Android" in user_agent:
            return "Android Device"
        else:
            return "Security Key"

    def _passkey_to_dict(self, passkey: Any) -> dict[str, Any]:
        """Convert passkey DB model to dict.

        Args:
            passkey: PasskeyDB model

        Returns:
            Dict with passkey details
        """
        transports = json.loads(passkey.transports) if passkey.transports else None

        return {
            "id": passkey.id,
            "name": passkey.name,
            "createdAt": passkey.created_at,
            "lastUsedAt": passkey.last_used_at,
            "isEnabled": passkey.is_enabled,
            "userAgent": passkey.user_agent,
            "aaguid": passkey.aaguid,
            "transports": transports,
            "backupEligible": passkey.backup_eligible,
            "backupState": passkey.backup_state,
        }
