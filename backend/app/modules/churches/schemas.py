"""Pydantic schemas for churches module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    suggestedRole: str | None = None
    showOnCard: bool = True
    phonePublic: bool = True
    emailPublic: bool = False


class ServiceAssignmentUpdateRequest(BaseModel):
    serviceTypeId: str | None = None
    customServiceName: str | None = None
    description: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    showOnCard: bool | None = None
    phonePublic: bool | None = None
    emailPublic: bool | None = None


class ServiceAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    personId: str = Field(validation_alias="person_id")
    serviceTypeId: str | None = Field(default=None, validation_alias="service_type_id")
    customServiceName: str | None = Field(default=None, validation_alias="custom_service_name")
    description: str | None = None
    scopeType: str = Field(validation_alias="scope_type")
    scopeId: str = Field(validation_alias="scope_id")
    showOnCard: bool = Field(validation_alias="show_on_card")
    phonePublic: bool = Field(validation_alias="phone_public")
    emailPublic: bool = Field(validation_alias="email_public")
    createdAt: datetime = Field(validation_alias="created_at")
    person: PersonResponse | None = None
    serviceType: ServiceTypeResponse | None = None


class PersonSearchResponse(BaseModel):
    persons: list[PersonResponse]
