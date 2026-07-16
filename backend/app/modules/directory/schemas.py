"""Pydantic schemas for the people directory (email export + person browser) module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DirectoryOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class DirectoryFiltersResponse(BaseModel):
    regions: list[DirectoryOption]
    serviceTypes: list[DirectoryOption]
    groups: list[DirectoryOption]


class DirectoryPersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    firstName: str | None = Field(default=None, validation_alias="first_name")
    lastName: str | None = Field(default=None, validation_alias="last_name")
    email: str


class DirectoryExportResponse(BaseModel):
    persons: list[DirectoryPersonResponse]


class PersonAffiliationResponse(BaseModel):
    kind: str  # "service" | "group"
    label: str
    context: str | None = None


class PersonBrowseResponse(BaseModel):
    id: str
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    affiliations: list[PersonAffiliationResponse] = []


class PersonListResponse(BaseModel):
    persons: list[PersonBrowseResponse]


class PersonUpdateRequest(BaseModel):
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None


class PersonMergeRequest(BaseModel):
    keepPersonId: str
    mergePersonId: str


PersonChangeLogField = Literal["firstName", "lastName", "email", "phone"]

PERSON_FIELD_LABELS: dict[str, str] = {
    "firstName": "Imię",
    "lastName": "Nazwisko",
    "email": "E-mail",
    "phone": "Telefon",
}


class PersonChangeLogEntry(BaseModel):
    id: str
    field: PersonChangeLogField
    field_label: str
    old_value: str | None
    new_value: str | None
    source: Literal["admin_manual"]
    actor_label: str
    created_at: datetime


class PersonChangeLogResponse(BaseModel):
    entries: list[PersonChangeLogEntry]
