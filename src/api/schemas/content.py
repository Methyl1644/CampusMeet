from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TagProposalCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    category: str = Field(min_length=1, max_length=40)
    source_text: str = Field(min_length=1, max_length=1000)
    suggested_tag_id: str = Field(default="", max_length=100)


class TagProposalReviewRequest(BaseModel):
    decision: Literal["approve", "merge", "reject"]
    target_tag_id: str = Field(default="", max_length=100)
    canonical_name: str = Field(default="", max_length=60)
    reason: str = Field(default="", max_length=500)


class TopicCreateRequest(BaseModel):
    channel: Literal["official", "organization"]
    title: str = Field(min_length=1, max_length=120)
    short_title: str = Field(min_length=1, max_length=60)
    organizer: str = Field(min_length=1, max_length=120)
    organizer_key: str = Field(min_length=1, max_length=100)
    canonical_event_key: str = Field(min_length=1, max_length=120)
    edition: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=600)
    content: str = Field(min_length=1, max_length=8000)
    source_url: str = Field(default="", max_length=500)
    cover_url: str = Field(default="", max_length=500)
    registration_deadline: datetime.datetime | None = None
    activity_start_at: datetime.datetime | None = None
    activity_end_at: datetime.datetime | None = None
    organization_id: int | None = Field(default=None, ge=1)
    tag_ids: list[str] = Field(min_length=1, max_length=8)


class TopicUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    short_title: str | None = Field(default=None, min_length=1, max_length=60)
    summary: str | None = Field(default=None, min_length=1, max_length=600)
    content: str | None = Field(default=None, min_length=1, max_length=8000)
    source_url: str | None = Field(default=None, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    tag_ids: list[str] | None = Field(default=None, min_length=1, max_length=8)


class TopicPostModerationRequest(BaseModel):
    status: Literal["recruiting", "closed", "hidden"]
    reason: str = Field(default="", max_length=500)


class CollaboratorInviteRequest(BaseModel):
    user_id: int = Field(ge=1)
    role: str = Field(min_length=1, max_length=40)
    expires_at: datetime.datetime | None = None
