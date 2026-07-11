"""Pydantic models for AI structured extraction."""

from pydantic import BaseModel, Field


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


class ExtractionResult(BaseModel):
    """Top-level shape the model must return."""

    congregations: list[ExtractedCongregation] = Field(default_factory=list)
