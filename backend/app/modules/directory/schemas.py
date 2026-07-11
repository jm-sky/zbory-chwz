"""Pydantic schemas for the people directory (email export) module."""

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
