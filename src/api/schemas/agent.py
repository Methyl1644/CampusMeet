from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PostDraftAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    draft: dict[str, Any] | str = Field(default_factory=dict)
    user_skills: list[str] | str = Field(default_factory=list)
    kind: Literal["topic_team", "casual_invitation"] = "casual_invitation"
    topic_id: str = Field(default="", max_length=40)
    field_states: dict[str, Any] = Field(default_factory=dict)


class ClassifyReviewRequest(BaseModel):
    title: str = Field(default="", max_length=120)
    activity_name: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=8000)
    persist_tag_proposals: bool = True


class MatchRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=40)


class TeamPlanRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=40)
