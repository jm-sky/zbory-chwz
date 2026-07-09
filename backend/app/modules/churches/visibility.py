"""Unified visibility levels for church platform content."""

from __future__ import annotations

from typing import Literal

VisibilityLevel = Literal["hidden", "public", "authenticated", "pastors"]

VISIBILITY_LEVELS: tuple[VisibilityLevel, ...] = (
    "hidden",
    "public",
    "authenticated",
    "pastors",
)

DEFAULT_CARD_VISIBILITY: VisibilityLevel = "public"
DEFAULT_PHONE_VISIBILITY: VisibilityLevel = "public"
DEFAULT_EMAIL_VISIBILITY: VisibilityLevel = "authenticated"


def is_valid_visibility(value: str) -> bool:
    return value in VISIBILITY_LEVELS


class VisibilityService:
    """Resolves whether a viewer can see content at a given visibility level."""

    @staticmethod
    def can_view(
        visibility: str,
        *,
        is_authenticated: bool,
        has_pastoral_access: bool,
    ) -> bool:
        if visibility == "hidden":
            return False
        if visibility == "public":
            return True
        if not is_authenticated:
            return False
        if visibility == "authenticated":
            return True
        if visibility == "pastors":
            return has_pastoral_access
        return False

    @staticmethod
    def filter_contact_field(
        value: str | None,
        visibility: str,
        *,
        is_authenticated: bool,
        has_pastoral_access: bool,
    ) -> str | None:
        if not value:
            return None
        if VisibilityService.can_view(
            visibility,
            is_authenticated=is_authenticated,
            has_pastoral_access=has_pastoral_access,
        ):
            return value
        return None
