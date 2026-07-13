"""Pydantic models for AI structured extraction."""

from pydantic import BaseModel, Field, field_validator

# Some models return the literal string "null" (or similar placeholders) for a
# missing field instead of a real JSON null, despite the strict schema - see
# docs/plans/2026-07-11--congregation-address-text-import.md. Left unnormalized,
# this string flows into the diff UI as a visible "null" and can even be
# proposed for saving over a real existing value.
_NULL_LIKE = {"null", "none", "n/a", "brak", ""}

_NULLABLE_FIELDS = (
    "street",
    "city",
    "postal_code",
    "province",
    "country",
    "contact_name",
    "contact_title",
    "contact_phone",
    "contact_email",
)


class ExtractedCongregation(BaseModel):
    """One congregation mention extracted from free-text notes."""

    name: str = Field(description="Congregation name as written in the text")
    street: str | None = None
    city: str | None = None
    postal_code: str | None = None
    province: str | None = Field(default=None, description="Polish voivodeship as an ASCII slug, e.g. 'lubuskie'")
    country: str | None = Field(default=None, description="ISO 3166-1 alpha-2 country code, e.g. 'PL'")
    contact_name: str | None = None
    contact_title: str | None = Field(default=None, description="e.g. 'Pastor', 'Diakon'")
    contact_phone: str | None = None
    contact_email: str | None = None

    @field_validator(*_NULLABLE_FIELDS, mode="before")
    @classmethod
    def _blank_null_like_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() in _NULL_LIKE:
            return None
        return value


class ExtractionResult(BaseModel):
    """Top-level shape the model must return."""

    congregations: list[ExtractedCongregation] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Second-pass trust assessment for a clergy e-mail update proposal.

    See docs/plans/2026-07-13--clergy-email-updates.md - gates whether an
    e-mail-sourced change can be auto-applied without admin review.
    """

    trust_score: float = Field(ge=0.0, le=1.0, description="0-1 confidence this update is legitimate and internally consistent")
    reasoning: str = Field(description="Short justification in Polish")
