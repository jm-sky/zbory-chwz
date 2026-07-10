"""Pydantic schemas for the people groups module."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GroupVisibility = Literal["public", "authenticated", "private"]
GroupScopeType = Literal["community", "region", "global"]


class GroupPersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    firstName: str | None = Field(default=None, validation_alias="first_name")
    lastName: str | None = Field(default=None, validation_alias="last_name")
    email: str | None = None
    phone: str | None = None


class GroupMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    groupId: str = Field(validation_alias="group_id")
    personId: str = Field(validation_alias="person_id")
    roleLabel: str | None = Field(default=None, validation_alias="role_label")
    joinedAt: datetime = Field(validation_alias="joined_at")
    leftAt: datetime | None = Field(default=None, validation_alias="left_at")
    person: GroupPersonResponse | None = None


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None = None
    scopeType: str = Field(validation_alias="scope_type")
    scopeId: str | None = Field(default=None, validation_alias="scope_id")
    visibility: str
    stewardUserId: str | None = Field(default=None, validation_alias="steward_user_id")
    createdAt: datetime = Field(validation_alias="created_at")
    updatedAt: datetime = Field(validation_alias="updated_at")
    memberCount: int = 0


class GroupDetailResponse(GroupResponse):
    memberships: list[GroupMembershipResponse] = []


class GroupCreateRequest(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    scopeType: GroupScopeType = "global"
    scopeId: str | None = None
    visibility: GroupVisibility = "authenticated"
    stewardUserId: str | None = None


class GroupUpdateRequest(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    scopeType: GroupScopeType | None = None
    scopeId: str | None = None
    visibility: GroupVisibility | None = None
    stewardUserId: str | None = None


class GroupMembershipCreateRequest(BaseModel):
    personId: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    roleLabel: str | None = None


class GroupMembershipUpdateRequest(BaseModel):
    roleLabel: str | None = None
