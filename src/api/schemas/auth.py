from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SendCodeRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    purpose: Literal["register", "login", "campus_verify", "reset_password"] = "register"


class RegisterRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=40)
    major: str = Field(default="", max_length=80)
    grade: str = Field(default="", max_length=40)
    skills: list[str] = Field(default_factory=list, max_length=30)
    wechat: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    account: str = Field(min_length=3, max_length=254)
    password: str = Field(default="", max_length=128)
    code: str = Field(default="", max_length=6)


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
