from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

from api.schemas.auth import OnboardingInterest
from services.onboarding import MAX_ONBOARDING_TEXT


LookingForItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]
SkillItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]


class PartialProfileVisibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major: StrictBool | None = None
    grade: StrictBool | None = None
    interests: StrictBool | None = None
    skills: StrictBool | None = None
    availability: StrictBool | None = None
    contact: StrictBool | None = None
    activities: StrictBool | None = None
    groups: StrictBool | None = None


class PartialAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday_daytime: StrictBool | None = None
    weekday_evening: StrictBool | None = None
    weekend_daytime: StrictBool | None = None
    weekend_evening: StrictBool | None = None
    weekly_hours: str | None = Field(default=None, max_length=40)


class NotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applications: StrictBool | None = None
    teams: StrictBool | None = None
    moderation: StrictBool | None = None
    deadlines: StrictBool | None = None
    messages: StrictBool | None = None


class ProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(default=None, max_length=40)
    avatar: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=80)
    grade: str | None = Field(default=None, max_length=40)
    interests: list[OnboardingInterest] | None = Field(default=None, max_length=30)
    looking_for: list[LookingForItem] | None = Field(default=None, max_length=12)
    skills: list[SkillItem] | None = Field(default=None, max_length=30)
    availability: PartialAvailabilityRequest | None = None
    bio: str | None = Field(default=None, max_length=500)
    profile_visibility: PartialProfileVisibilityRequest | None = None
    wechat: str | None = Field(default=None, max_length=80)

    @field_validator("interests", mode="before")
    @classmethod
    def strip_interest_items(cls, value):
        if not isinstance(value, list):
            return value
        return [item.strip() if isinstance(item, str) else item for item in value]

    @model_validator(mode="after")
    def validate_total_text_size(self):
        if _text_size(self.model_dump(exclude_none=True)) > MAX_ONBOARDING_TEXT:
            raise ValueError(f"资料文本总量不能超过 {MAX_ONBOARDING_TEXT} 个字符")
        return self


class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_visibility: PartialProfileVisibilityRequest | None = None
    notification_preferences: NotificationPreferencesRequest | None = None


def _text_size(value: object) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        return sum(_text_size(item) for item in value.values())
    if isinstance(value, list):
        return sum(_text_size(item) for item in value)
    return 0
