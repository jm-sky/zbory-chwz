"""Tests for visibility resolution."""

import pytest

from app.modules.churches.visibility import VisibilityService


@pytest.mark.parametrize(
    ("visibility", "is_authenticated", "has_pastoral_access", "expected"),
    [
        ("hidden", False, False, False),
        ("hidden", True, True, False),
        ("public", False, False, True),
        ("public", True, True, True),
        ("authenticated", False, False, False),
        ("authenticated", True, False, True),
        ("pastors", True, False, False),
        ("pastors", True, True, True),
    ],
)
def test_can_view(
    visibility: str,
    is_authenticated: bool,
    has_pastoral_access: bool,
    expected: bool,
) -> None:
    assert (
        VisibilityService.can_view(
            visibility,
            is_authenticated=is_authenticated,
            has_pastoral_access=has_pastoral_access,
        )
        is expected
    )


def test_filter_contact_field() -> None:
    assert (
        VisibilityService.filter_contact_field(
            "+48123456789",
            "authenticated",
            is_authenticated=False,
            has_pastoral_access=False,
        )
        is None
    )
    assert (
        VisibilityService.filter_contact_field(
            "a@b.c",
            "authenticated",
            is_authenticated=True,
            has_pastoral_access=False,
        )
        == "a@b.c"
    )
