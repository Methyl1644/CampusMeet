from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ShortRole = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
TagId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PostCreateRequest(RequestModel):
    title: str | None = Field(default=None, max_length=120)
    description: str = Field(default="", max_length=5000)
    main_category: Literal[
        "竞赛与项目",
        "学习与科研",
        "体育与健身",
        "旅行与户外",
        "校园生活",
        "拼团与AA",
    ] | None = None
    activity_name: str | None = Field(default=None, max_length=120)
    target_members: int = Field(default=1, ge=1, le=100)
    needed_roles: list[ShortRole] = Field(default_factory=list, max_length=10)
    weekly_hours: str = Field(default="", max_length=80)
    school_scope: str = Field(default="", max_length=80)
    deadline: str = Field(default="", max_length=80)
    kind: Literal["topic_team", "casual_invitation"] = "casual_invitation"
    topic_id: int | None = Field(default=None, ge=1)
    tag_ids: list[TagId] = Field(default_factory=list, max_length=8)
    tags: list[TagId] | None = Field(default=None, max_length=8)

    @model_validator(mode="after")
    def require_title_or_activity(self) -> "PostCreateRequest":
        if not self.title and not self.activity_name:
            raise ValueError("title or activity_name is required")
        return self


class PostUpdateRequest(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    main_category: Literal[
        "竞赛与项目",
        "学习与科研",
        "体育与健身",
        "旅行与户外",
        "校园生活",
        "拼团与AA",
    ] | None = None
    activity_name: str | None = Field(default=None, min_length=1, max_length=120)
    target_members: int | None = Field(default=None, ge=1, le=100)
    needed_roles: list[ShortRole] | None = Field(default=None, max_length=10)
    weekly_hours: str | None = Field(default=None, max_length=80)
    school_scope: str | None = Field(default=None, max_length=80)
    deadline: str | None = Field(default=None, max_length=80)
    tag_ids: list[TagId] | None = Field(default=None, max_length=8)

    @model_validator(mode="after")
    def require_change(self) -> "PostUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class ApplicationCreateRequest(RequestModel):
    post_id: int = Field(gt=0)
    role_wanted: str = Field(min_length=1, max_length=80)
    experience: str = Field(min_length=1, max_length=2000)
    available_time: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)
    questions: list[Question] = Field(default_factory=list, max_length=10)


class MessageSendRequest(RequestModel):
    content: str = Field(min_length=1, max_length=2000)


class TeamTaskRequest(RequestModel):
    title: str = Field(min_length=1, max_length=120)
    assignee_id: int | None = Field(default=None, gt=0)
    due_at: str = Field(default="", max_length=40)


class TeamTaskDoneRequest(RequestModel):
    done: bool


class TeamTaskOrderRequest(RequestModel):
    task_ids: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]] = Field(
        min_length=1,
        max_length=100,
    )


class TeamMemberRoleRequest(RequestModel):
    suggested_role: str = Field(min_length=1, max_length=80)


class TeamOwnerTransferRequest(RequestModel):
    target_user_id: int = Field(gt=0)
