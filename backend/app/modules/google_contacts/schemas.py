"""Pydantic schemas for the Google Contacts module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

GoogleContactsConnectionScope = Literal["readonly", "readonly_write"]
GoogleContactType = Literal["church", "person"]


class GoogleContactsAuthUrlResponse(BaseModel):
    authUrl: str
    state: str


class GoogleContactsCallbackRequest(BaseModel):
    code: str
    state: str


class GoogleContactsConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connected: bool
    scope: GoogleContactsConnectionScope | None = None
    connectedAt: datetime | None = Field(default=None, validation_alias="connected_at")
    expiresAt: datetime | None = Field(default=None, validation_alias="expires_at")


class GoogleContactSuggestion(BaseModel):
    """A single Google contact matching the "zbór"/"chwz" text filter."""

    resourceName: str
    displayName: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    organizationName: str | None = None
    emailAddresses: list[str] = Field(default_factory=list)
    phoneNumbers: list[str] = Field(default_factory=list)
    notes: str | None = None
    suggestedType: GoogleContactType
    addressStreet: str | None = None
    addressCity: str | None = None
    addressPostalCode: str | None = None
    addressProvince: str | None = None
    addressCountry: str | None = None


class GoogleContactsListResponse(BaseModel):
    contacts: list[GoogleContactSuggestion]
    totalFetched: int
    matchedCount: int


# Phase 2/3 — mapping screen (classify/match) and import to the database.
# See docs/plans/2026-07-10--google-contacts-sync.md decisions #4-#7.


class GoogleContactImportSelection(BaseModel):
    """A contact the admin picked on the list screen, with the (possibly
    corrected) classification they chose."""

    contact: GoogleContactSuggestion
    type: GoogleContactType


class GoogleContactsAnalyzeRequest(BaseModel):
    items: list[GoogleContactImportSelection]


class GoogleContactChurchProposal(BaseModel):
    """Proposed church (tenant) match/create for one Google contact."""

    resourceName: str
    matchType: Literal["matched", "new"]
    tenantId: str | None = None
    matchedName: str | None = None
    confidence: float = Field(ge=0, le=100)
    name: str
    street: str | None = None
    city: str | None = None
    postalCode: str | None = None
    province: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None


class GoogleContactPersonProposal(BaseModel):
    """Proposed person match/create for one Google contact."""

    resourceName: str
    matchType: Literal["matched", "new"]
    personId: str | None = None
    matchedName: str | None = None
    matchedBy: Literal["email", "phone"] | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None


class GoogleContactsCandidateTenant(BaseModel):
    tenantId: str
    name: str


class GoogleContactsServiceType(BaseModel):
    id: str
    name: str


class GoogleContactsAnalyzeResponse(BaseModel):
    churchProposals: list[GoogleContactChurchProposal]
    personProposals: list[GoogleContactPersonProposal]
    candidateTenants: list[GoogleContactsCandidateTenant]
    serviceTypes: list[GoogleContactsServiceType]


class GoogleContactChurchApplyItem(BaseModel):
    resourceName: str
    action: Literal["create", "update", "skip"]
    tenantId: str | None = None
    name: str | None = None
    street: str | None = None
    city: str | None = None
    postalCode: str | None = None
    province: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None

    @model_validator(mode="after")
    def check_required_target(self) -> "GoogleContactChurchApplyItem":
        if self.action == "update" and not self.tenantId:
            raise ValueError("tenantId is required when action is 'update'")
        if self.action == "create" and not self.name:
            raise ValueError("name is required when action is 'create'")
        return self


class GoogleContactPersonApplyItem(BaseModel):
    resourceName: str
    action: Literal["create", "update", "skip"]
    personId: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    assignToChurch: bool = False
    churchId: str | None = None
    serviceTypeId: str | None = None
    customServiceName: str | None = None

    @model_validator(mode="after")
    def check_required_target(self) -> "GoogleContactPersonApplyItem":
        if self.action == "update" and not self.personId:
            raise ValueError("personId is required when action is 'update'")
        if self.action != "skip" and self.assignToChurch:
            if not self.churchId:
                raise ValueError("churchId is required when assignToChurch is true")
            if not self.serviceTypeId and not self.customServiceName:
                raise ValueError("serviceTypeId or customServiceName is required when assignToChurch is true")
        return self


class GoogleContactsApplyRequest(BaseModel):
    churchItems: list[GoogleContactChurchApplyItem] = Field(default_factory=list)
    personItems: list[GoogleContactPersonApplyItem] = Field(default_factory=list)


class GoogleContactsApplyResponse(BaseModel):
    churchesCreated: int
    churchesUpdated: int
    personsCreated: int
    personsUpdated: int
    skipped: int
