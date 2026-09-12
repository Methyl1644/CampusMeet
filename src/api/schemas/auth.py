from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
    model_validator,
)

from services.onboarding import MAX_ONBOARDING_TEXT, ONBOARDING_INTERESTS


OnboardingInterest = Literal[*ONBOARDING_INTERESTS]
LookingForItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)
]
SkillItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]


class AvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday_daytime: StrictBool | None = None
    weekday_evening: StrictBool | None = None
    weekend_daytime: StrictBool | None = None
    weekend_evening: StrictBool | None = None
    weekly_hours: Literal[
        "",
        "每周 1-3 小时",
        "每周 4-6 小时",
        "每周 7-10 小时",
        "每周 10 小时以上",
    ] | None = None


class ProfileVisibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    major: StrictBool = True
    grade: StrictBool = True
    interests: StrictBool = True
    skills: StrictBool = True
    availability: StrictBool = False
    contact: StrictBool = False


class SendCodeRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    purpose: Literal["register", "campus_verify", "reset_password"] = "register"


class RegisterRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AccountDeactivateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


class PasswordResetRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


class AccountRequestCreate(BaseModel):
    request_type: Literal["data_export", "account_deletion"]


class CampusEmailVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)


class ProfileUpdateRequest(BaseModel):
    nickname: str = Field(default="", max_length=40)
    major: str = Field(default="", max_length=80)
    grade: str = Field(default="", max_length=40)
    skills: list[str] | str = Field(default_factory=list)
    wechat: str = Field(default="", max_length=80)


class OnboardingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=1, le=6)
    nickname: str | None = Field(default=None, max_length=40)
    avatar: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=80)
    grade: str | None = Field(default=None, max_length=40)
    interests: list[OnboardingInterest] | None = Field(default=None, max_length=30)
    looking_for: list[LookingForItem] | None = Field(default=None, max_length=12)
    skills: list[SkillItem] | None = Field(default=None, max_length=30)
    availability: AvailabilityRequest | None = None
    bio: str | None = Field(default=None, max_length=500)
    profile_visibility: ProfileVisibilityRequest | None = None

    @field_validator("interests", mode="before")
    @classmethod
    def strip_interest_items(cls, value):
        if not isinstance(value, list):
            return value
        return [item.strip() if isinstance(item, str) else item for item in value]

    @model_validator(mode="after")
    def validate_total_text_size(self):
        def text_size(value: object) -> int:
            if isinstance(value, str):
                return len(value)
            if isinstance(value, dict):
                return sum(text_size(item) for item in value.values())
            if isinstance(value, list):
                return sum(text_size(item) for item in value)
            return 0

        if text_size(self.model_dump(exclude_none=True)) > MAX_ONBOARDING_TEXT:
            raise ValueError(
                f"onboarding 文本总量不能超过 {MAX_ONBOARDING_TEXT} 个字符"
            )
        return self
