"""Pydantic schemas for tenant endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    status: str | None = Field(default="draft", max_length=32)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=512)
    status: str | None = Field(default=None, max_length=32)


class TenantResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str | None = None
    role: str
    createdAt: datetime


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]


class TenantMembershipResponse(BaseModel):
    tenant_id: str
    user_id: str
    user_name: str | None = None
    user_email: str | None = None
    role: str
    createdAt: datetime


class TenantMembershipCreateRequest(BaseModel):
    user_id: str
    role: str = Field(default="member", max_length=32)


class TenantMembershipUpdateRequest(BaseModel):
    role: str = Field(max_length=32)
