"""Pydantic schemas for the Google Contacts module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    organizationName: str | None = None
    emailAddresses: list[str] = Field(default_factory=list)
    phoneNumbers: list[str] = Field(default_factory=list)
    notes: str | None = None
    suggestedType: GoogleContactType


class GoogleContactsListResponse(BaseModel):
    contacts: list[GoogleContactSuggestion]
    totalFetched: int
    matchedCount: int
