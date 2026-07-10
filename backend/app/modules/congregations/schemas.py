"""Pydantic schemas for congregation endpoints."""

from datetime import datetime

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


class ContactPersonResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    order: int
    created_at: datetime
    updated_at: datetime


class ContactPersonCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    order: int = Field(default=0, ge=0)


class ContactPersonUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    order: int | None = Field(default=None, ge=0)


class CongregationFullResponse(BaseModel):
    """Full congregation data including address, service times, and contact persons."""

    tenant_id: str
    address: AddressResponse | None = None
    service_times: list[ServiceTimeResponse] = []
    contact_persons: list[ContactPersonResponse] = []
