from __future__ import annotations

from typing import Literal

from pydantic import Field

from api.schemas.collaboration import RequestModel


class PlatformRoleInviteRequest(RequestModel):
    user_id: int = Field(gt=0)
    role: Literal["operator", "senior_operator"]


class PlatformRoleAcceptRequest(RequestModel):
    password: str = Field(min_length=8, max_length=128)


class PlatformRoleActionRequest(RequestModel):
    reason: str = Field(min_length=2, max_length=500)
