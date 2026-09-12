from __future__ import annotations

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


ParticipationMode = Literal["open_team", "official_signup", "information_only"]
PostPurpose = Literal["team_recruitment", "official_signup", "discussion"]
JoinMode = Literal["application", "direct", "none"]
JoinState = Literal["owner", "joined", "pending", "rejected", "available", "closed"]


class ExploreResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExploreTag(ExploreResponseModel):
    tag_id: str
    canonical_name: str
    category: str
    display_color: str


class ExploreUserSummary(ExploreResponseModel):
    id: str
    nickname: str
    avatar: str | None
    major: str | None
    grade: str | None


class ExploreOfficialTrustBadge(ExploreResponseModel):
    kind: Literal["platform_official"]
    label: str


class ExploreVerifiedOrganizationTrustBadge(ExploreResponseModel):
    kind: Literal["verified_organization"]
    label: str
    organization_name: str


ExploreTrustBadge = Annotated[
    ExploreOfficialTrustBadge | ExploreVerifiedOrganizationTrustBadge,
    Field(discriminator="kind"),
]


class ExploreResponsiblePerson(ExploreResponseModel):
    user_id: str
    nickname: str
    role: str
    badge: str


class ExploreLinkedActivity(ExploreResponseModel):
    id: str
    title: str
    short_title: str
    organizer: str
    cover_url: str | None
    cover_placeholder_key: str
    registration_deadline: datetime.datetime | None
    activity_start_at: datetime.datetime | None
    participation_mode: ParticipationMode
    status: str


class ExploreGroupCard(ExploreResponseModel):
    id: str
    title: str
    description: str | None
    source_type: str
    kind: Literal["topic_team", "casual_invitation"]
    purpose: PostPurpose
    join_mode: JoinMode
    topic_id: str | None
    main_category: str
    activity_name: str
    cover_url: str | None
    cover_placeholder_key: str
    current_members: int
    target_members: int
    needed_roles: list[str]
    weekly_hours: str | None
    school_scope: str | None
    deadline: str | None
    risk_level: str
    status: Literal["recruiting", "full", "closed"]
    author_id: str
    author: ExploreUserSummary | None
    bookmark: bool
    join_state: JoinState
    member_preview: list[ExploreUserSummary] = Field(max_length=8)
    linked_activity: ExploreLinkedActivity | None
    tags: list[ExploreTag]
    collaborators: list[ExploreResponsiblePerson]
    created_at: datetime.datetime | None


class ExploreGroupDetail(ExploreGroupCard):
    pass


class ExploreActivityCard(ExploreResponseModel):
    id: str
    channel: Literal["official", "organization"]
    title: str
    short_title: str
    organizer: str
    edition: str
    summary: str
    content: str
    source_url: str | None
    source_status: str
    cover_url: str | None
    cover_placeholder_key: str
    location_name: str | None
    campus_scope: str | None
    capacity: int | None
    registration_deadline: datetime.datetime | None
    activity_start_at: datetime.datetime | None
    activity_end_at: datetime.datetime | None
    follower_count: int
    participant_count: int
    participant_preview: list[ExploreUserSummary] = Field(max_length=8)
    participation_mode: ParticipationMode
    favorite: bool
    followed: bool
    participation_state: JoinState
    tags: list[ExploreTag]
    status: Literal["active"]
    trust_badges: list[ExploreTrustBadge]
    responsible_people: list[ExploreResponsiblePerson]


class ExploreActivityDetail(ExploreActivityCard):
    related_groups: list[ExploreGroupCard] = Field(max_length=8)


class ExploreActivityPage(ExploreResponseModel):
    list: list[ExploreActivityCard]
    total: int
    page: int
    page_size: int = Field(le=40)
    pages: int


class ExploreGroupPage(ExploreResponseModel):
    list: list[ExploreGroupCard]
    total: int
    page: int
    page_size: int = Field(le=40)
    pages: int


class ExploreActivityListResponse(ExploreResponseModel):
    code: Literal[0]
    message: str
    data: ExploreActivityPage


class ExploreGroupListResponse(ExploreResponseModel):
    code: Literal[0]
    message: str
    data: ExploreGroupPage


class ExploreActivityDetailResponse(ExploreResponseModel):
    code: Literal[0]
    message: str
    data: ExploreActivityDetail


class ExploreGroupDetailResponse(ExploreResponseModel):
    code: Literal[0]
    message: str
    data: ExploreGroupDetail
