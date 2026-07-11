"""Pydantic schemas for tenant endpoints."""

from datetime import datetime
from typing import Literal

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
    deletedAt: datetime | None = None


class TenantListResponse(BaseModel):
    tenants: list[TenantResponse]


class PublicCardContact(BaseModel):
    """Public contact shown on a congregation card."""

    name: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None


class PublicCongregationResponse(BaseModel):
    """Public congregation data with basic address, service times, and contact info."""

    id: str
    name: str
    description: str | None = None
    status: str | None = None
    createdAt: datetime
    # "church" for a congregation, "branch" for a placówka belonging to one
    type: Literal["church", "branch"] = "church"
    # Set on branches: the id and name of the congregation they belong to
    parent_id: str | None = None
    parent_name: str | None = None
    # Address info
    city: str | None = None
    street: str | None = None
    postal_code: str | None = None
    province: str | None = None
    country: str | None = None
    # Service times (first few)
    service_times: list[dict[str, str]] = []  # [{"day": "niedziela", "time": "11:00"}]
    # Contacts from public service assignments
    card_contacts: list[PublicCardContact] = []
    # Legacy single contact (first card_contacts entry)
    contact_name: str | None = None
    contact_title: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class PublicCongregationListResponse(BaseModel):
    congregations: list[PublicCongregationResponse]


class CongregationBranchSummary(BaseModel):
    """A branch (placówka) listed on its parent congregation's detail page."""

    id: str
    name: str


class CongregationDetailResponse(BaseModel):
    """Full congregation detail, with fields filtered by the viewer's visibility level."""

    id: str
    name: str
    description: str | None = None
    status: str | None = None
    createdAt: datetime
    # Address info
    city: str | None = None
    street: str | None = None
    postal_code: str | None = None
    province: str | None = None
    country: str | None = None
    # Full (unlimited) service times
    service_times: list[dict[str, str]] = []
    # All service assignments; phone/email filtered by per-field visibility
    card_contacts: list[PublicCardContact] = []
    # Publicly visible branches (placówki) of this congregation
    branches: list[CongregationBranchSummary] = []
    # The viewer's membership role in this congregation, if any
    role: str | None = None
    # Whether the viewer may edit this congregation (member or global admin/owner)
    canManage: bool = False


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
