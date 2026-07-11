"""Pydantic schemas for churches module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VisibilityLevel = Literal["hidden", "public", "authenticated", "pastors"]
ChurchAclRole = Literal["bishop", "regional_bishop", "pastor", "diacon"]


class RegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    communityId: str = Field(validation_alias="community_id")
    name: str
    slug: str


class ChurchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    communityId: str = Field(validation_alias="community_id")
    regionId: str | None = Field(default=None, validation_alias="region_id")
    tenantId: str = Field(validation_alias="tenant_id")
    name: str
    visibility: str
    createdAt: datetime = Field(validation_alias="created_at")


class BranchCreateRequest(BaseModel):
    name: str
    slug: str | None = None
    visibility: str = "hidden"


class BranchUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    visibility: str | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    churchId: str = Field(validation_alias="church_id")
    name: str
    slug: str
    visibility: str
    createdAt: datetime = Field(validation_alias="created_at")


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    firstName: str | None = Field(default=None, validation_alias="first_name")
    lastName: str | None = Field(default=None, validation_alias="last_name")
    email: str | None = None
    phone: str | None = None
    userId: str | None = Field(default=None, validation_alias="user_id")


class ServiceTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    scopeType: str = Field(validation_alias="scope_type")
    suggestedRole: str | None = Field(default=None, validation_alias="suggested_role")
    isSeniorTier: bool = Field(validation_alias="is_senior_tier")
    sortOrder: int = Field(validation_alias="sort_order")


class ServiceAssignmentCreateRequest(BaseModel):
    personId: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    serviceTypeId: str | None = None
    customServiceName: str | None = None
    description: str | None = None
    createAccount: bool = False
    suggestedRole: ChurchAclRole | None = None
    cardVisibility: VisibilityLevel = "public"
    phoneVisibility: VisibilityLevel = "public"
    emailVisibility: VisibilityLevel = "authenticated"
    sortOrder: int | None = Field(default=None, ge=0)


class ServiceAssignmentUpdateRequest(BaseModel):
    serviceTypeId: str | None = None
    customServiceName: str | None = None
    description: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    cardVisibility: VisibilityLevel | None = None
    phoneVisibility: VisibilityLevel | None = None
    emailVisibility: VisibilityLevel | None = None
    sortOrder: int | None = Field(default=None, ge=0)


class ServiceAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    personId: str = Field(validation_alias="person_id")
    serviceTypeId: str | None = Field(default=None, validation_alias="service_type_id")
    customServiceName: str | None = Field(
        default=None, validation_alias="custom_service_name"
    )
    description: str | None = None
    scopeType: str = Field(validation_alias="scope_type")
    scopeId: str = Field(validation_alias="scope_id")
    cardVisibility: str = Field(validation_alias="card_visibility")
    phoneVisibility: str = Field(validation_alias="phone_visibility")
    emailVisibility: str = Field(validation_alias="email_visibility")
    sortOrder: int = Field(validation_alias="sort_order")
    createdAt: datetime = Field(validation_alias="created_at")
    person: PersonResponse | None = None
    serviceType: ServiceTypeResponse | None = Field(
        default=None, validation_alias="service_type"
    )


class PersonSearchResponse(BaseModel):
    persons: list[PersonResponse]
