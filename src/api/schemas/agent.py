from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


MAX_AGENT_STRUCTURE_BYTES = 32_768
MAX_AGENT_STRUCTURE_DEPTH = 6
MAX_AGENT_COLLECTION_ITEMS = 100
MAX_AGENT_VALUE_LENGTH = 8_000


def _validate_structure(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_AGENT_STRUCTURE_DEPTH:
        raise ValueError("structured context is too deeply nested")
    if isinstance(value, dict):
        if len(value) > MAX_AGENT_COLLECTION_ITEMS:
            raise ValueError("structured context contains too many fields")
        for key, item in value.items():
            if len(str(key)) > 120:
                raise ValueError("structured context contains an oversized field name")
            _validate_structure(item, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_AGENT_COLLECTION_ITEMS:
            raise ValueError("structured context contains too many items")
        for item in value:
            _validate_structure(item, depth=depth + 1)
    elif isinstance(value, str) and len(value) > MAX_AGENT_VALUE_LENGTH:
        raise ValueError("structured context contains an oversized value")
    return value


def _validate_agent_context(value: Any) -> Any:
    _validate_structure(value)
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_AGENT_STRUCTURE_BYTES:
        raise ValueError("structured context is too large")
    return value


class PostDraftAgentRequest(BaseModel):
    message: str = Field(min_length=0, max_length=4000)
    draft: dict[str, Any] | str = Field(default_factory=dict)
    user_skills: list[str] | str = Field(default_factory=list)
    kind: Literal["topic_team", "casual_invitation"] = "casual_invitation"
    topic_id: str = Field(default="", max_length=40)
    field_states: dict[str, Any] = Field(default_factory=dict)
    workflow_draft: dict[str, Any] = Field(default_factory=dict)
    workflow_field_states: dict[str, Any] = Field(default_factory=dict)
    purpose: Literal["team_recruitment", "official_signup", "discussion"] | None = None
    publish_context_revision: str | None = Field(default=None, max_length=64)

    @field_validator("draft", "field_states", "workflow_draft", "workflow_field_states")
    @classmethod
    def validate_structured_context(cls, value: Any) -> Any:
        return _validate_agent_context(value)

    @field_validator("user_skills")
    @classmethod
    def validate_user_skills(cls, value: list[str] | str) -> list[str] | str:
        if isinstance(value, str):
            if len(value) > 4_000:
                raise ValueError("user skill context is too large")
            return value
        if len(value) > 40 or any(len(item) > 120 for item in value):
            raise ValueError("user skill context is too large")
        return value


class ClassifyReviewRequest(BaseModel):
    title: str = Field(default="", max_length=120)
    activity_name: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=8000)
    persist_tag_proposals: bool = True


class MatchRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=40)


class TeamPlanRequest(BaseModel):
    team_id: str = Field(min_length=1, max_length=40)
