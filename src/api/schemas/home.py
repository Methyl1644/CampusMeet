from __future__ import annotations

import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class HomeResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HomeProfile(HomeResponseModel):
    id: str
    nickname: str
    avatar: str | None
    major: str | None
    grade: str | None


class HomeTag(HomeResponseModel):
    tag_id: str
    canonical_name: str
    category: str
    display_color: str


class HomeOfficialTrustBadge(HomeResponseModel):
    kind: Literal["platform_official"]
    label: str


class HomeVerifiedOrganizationTrustBadge(HomeResponseModel):
    kind: Literal["verified_organization"]
    label: str
    organization_name: str


HomeTrustBadge = Annotated[
    HomeOfficialTrustBadge | HomeVerifiedOrganizationTrustBadge,
    Field(discriminator="kind"),
]


class HomeResponsiblePerson(HomeResponseModel):
    user_id: str
    nickname: str
    role: str
    badge: str


class HomeTopic(HomeResponseModel):
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
    follower_count: int
    followed: bool
    tags: list[HomeTag]
    status: Literal["active"]
    trust_badges: list[HomeTrustBadge]
    responsible_people: list[HomeResponsiblePerson]
    registration_deadline: datetime.datetime | None
    activity_start_at: datetime.datetime | None
    activity_end_at: datetime.datetime | None


class RecommendedHomeTopic(HomeTopic):
    recommendation_reason: str


class HomeDeadlineReminder(HomeTopic):
    days_remaining: int


class HomeJoinedGroup(HomeResponseModel):
    id: str
    post_id: str
    activity_name: str
    member_role: Literal["owner", "member"]
    created_at: datetime.datetime
    current_members: int
    target_members: int


class HomeTimelineItem(HomeResponseModel):
    team_id: str
    team_name: str
    task_id: str
    title: str
    due_at: datetime.datetime | None
    done: bool


class HomeUnread(HomeResponseModel):
    messages: int
    notifications: int


HomeWarningSection = Literal[
    "deadline_reminder",
    "recommended_topics",
    "attending_topics",
    "followed_topics",
    "joined_groups",
    "group_timeline",
    "unread",
]


class HomeFeed(HomeResponseModel):
    profile: HomeProfile
    deadline_reminder: HomeDeadlineReminder | None
    recommended_topics: list[RecommendedHomeTopic]
    attending_topics: list[HomeTopic]
    followed_topics: list[HomeTopic]
    joined_groups: list[HomeJoinedGroup]
    group_timeline: list[HomeTimelineItem]
    unread: HomeUnread
    warnings: list[HomeWarningSection]


class HomeFeedResponse(HomeResponseModel):
    code: Literal[0]
    message: str
    data: HomeFeed
