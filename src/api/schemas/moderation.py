from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    target_type: Literal["post", "topic", "message", "user"]
    target_id: str = Field(min_length=1, max_length=120)
    reason_code: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)


class CaseResolutionRequest(BaseModel):
    resolution: str = Field(min_length=1, max_length=500)


class RestrictionCreateRequest(BaseModel):
    user_id: int = Field(ge=1)
    restriction_type: Literal["posting", "messaging", "applications", "all_interactions"]
    reason_code: str = Field(min_length=1, max_length=100)
    expires_at: datetime.datetime


class AppealCreateRequest(BaseModel):
    case_id: int = Field(ge=1)
    statement: str = Field(min_length=1, max_length=4000)


class AppealReviewRequest(BaseModel):
    outcome: Literal["approved", "rejected"]
    resolution: str = Field(min_length=1, max_length=500)
