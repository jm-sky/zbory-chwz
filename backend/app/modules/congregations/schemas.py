"""Pydantic schemas for congregation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.congregations.geo import (
    COUNTRY_CODE_PATTERN,
    DEFAULT_COUNTRY,
    is_valid_province,
)


class AddressResponse(BaseModel):
    id: str
    tenant_id: str
    street: str | None = None
    city: str
    postal_code: str | None = None
    province: str | None = None
    country: str
    status: str
    created_at: datetime
    updated_at: datetime


class AddressCreateRequest(BaseModel):
    street: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    province: str | None = Field(default=None, max_length=100)
    country: str = Field(default=DEFAULT_COUNTRY, pattern=COUNTRY_CODE_PATTERN)
    status: str = Field(default="draft", max_length=32)

    @model_validator(mode="after")
    def check_province_belongs_to_country(self) -> "AddressCreateRequest":
        if not is_valid_province(self.country, self.province):
            raise ValueError(f"{self.province!r} is not a province of {self.country}")
        return self


class AddressUpdateRequest(BaseModel):
    street: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    province: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, pattern=COUNTRY_CODE_PATTERN)
    status: str | None = Field(default=None, max_length=32)


class ServiceTimeResponse(BaseModel):
    id: str
    tenant_id: str
    day: str
    time: str
    order: int
    created_at: datetime


class ServiceTimeCreateRequest(BaseModel):
    day: str = Field(min_length=1, max_length=50)
    time: str = Field(min_length=1, max_length=10)
    order: int = Field(default=0, ge=0)


class ServiceTimeUpdateRequest(BaseModel):
    day: str | None = Field(default=None, min_length=1, max_length=50)
    time: str | None = Field(default=None, min_length=1, max_length=10)
    order: int | None = Field(default=None, ge=0)


class CongregationFullResponse(BaseModel):
    """Full congregation data including address and service times."""

    tenant_id: str
    address: AddressResponse | None = None
    service_times: list[ServiceTimeResponse] = []


# Text-to-address import (paste free-text notes, review a diff, then apply)

ImportFieldKey = Literal[
    "street",
    "city",
    "postal_code",
    "province",
    "country",
    "contact_name",
    "contact_title",
    "contact_phone",
    "contact_email",
]


class ImportAnalyzeRequest(BaseModel):
    raw_text: str = Field(min_length=1)


class ImportFieldChange(BaseModel):
    """One field's current value vs. the AI-extracted value, for the review screen."""

    field: ImportFieldKey
    label: str
    group: Literal["address", "contact"]
    old_value: str | None = None
    new_value: str | None = None


class ImportCandidateTenant(BaseModel):
    """A tenant the admin can manually pick instead of the auto-match."""

    tenant_id: str
    name: str


class ImportProposal(BaseModel):
    proposal_id: str
    detected_name: str
    match_type: Literal["matched", "new"]
    tenant_id: str | None = None
    matched_name: str | None = None
    confidence: float = Field(ge=0, le=100)
    contact_context: str | None = None
    contact_person_id: str | None = None
    fields: list[ImportFieldChange]


class ImportAnalyzeResponse(BaseModel):
    proposals: list[ImportProposal]
    candidates: list[ImportCandidateTenant]


class ImportApplyField(BaseModel):
    field: ImportFieldKey
    value: str | None = None
    apply: bool = True


class ImportApplyItem(BaseModel):
    action: Literal["update", "create", "skip"]
    tenant_id: str | None = None
    congregation_name: str | None = None
    contact_person_id: str | None = None
    fields: list[ImportApplyField] = []

    @model_validator(mode="after")
    def check_required_target(self) -> "ImportApplyItem":
        if self.action == "update" and not self.tenant_id:
            raise ValueError("tenant_id is required when action is 'update'")
        if self.action == "create" and not self.congregation_name:
            raise ValueError("congregation_name is required when action is 'create'")
        return self


class ImportApplyRequest(BaseModel):
    items: list[ImportApplyItem]


class ImportApplyResponse(BaseModel):
    created: int
    updated: int
    skipped: int
