from __future__ import annotations

import datetime
from typing import Literal

from pydantic import Field, model_validator

from api.schemas.collaboration import RequestModel


class OrganizationApplicationRequest(RequestModel):
    organization_name: str = Field(min_length=2, max_length=100)
    org_type: Literal["student_org", "department", "laboratory", "administrative", "other"]
    school_scope: str = Field(min_length=2, max_length=200)
    official_email: str | None = Field(default=None, max_length=120)
    official_page: str | None = Field(default=None, max_length=500)
    responsible_person_statement: str = Field(min_length=10, max_length=2000)
    evidence_reference: str | None = Field(default=None, max_length=500)
    evidence: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_evidence(self) -> "OrganizationApplicationRequest":
        if not self.evidence_reference and not self.evidence:
            raise ValueError("evidence_reference is required")
        return self


class OrganizationReviewRequest(RequestModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(default="", max_length=500)
    validity_days: int = Field(default=365, ge=30, le=730)

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "OrganizationReviewRequest":
        if self.decision == "reject" and len(self.reason) < 2:
            raise ValueError("reason is required when rejecting an application")
        return self


class OrganizationInvitationRequest(RequestModel):
    user_id: int = Field(gt=0)
    role: Literal["publisher", "member"]
    expires_at: datetime.datetime | None = None

    @model_validator(mode="after")
    def require_future_expiry(self) -> "OrganizationInvitationRequest":
        if self.expires_at is None:
            return self
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        if expires_at <= datetime.datetime.now(datetime.timezone.utc):
            raise ValueError("expires_at must be in the future")
        return self


class OrganizationRenewalRequest(RequestModel):
    school_scope: str = Field(min_length=2, max_length=200)
    official_page: str | None = Field(default=None, max_length=500)
    responsible_person_statement: str = Field(min_length=10, max_length=2000)
    evidence_reference: str = Field(min_length=1, max_length=500)


class OwnershipTransferRequest(RequestModel):
    target_user_id: int = Field(gt=0)
    expires_at: datetime.datetime | None = None

    @model_validator(mode="after")
    def require_future_expiry(self) -> "OwnershipTransferRequest":
        if self.expires_at is None:
            return self
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        if expires_at <= datetime.datetime.now(datetime.timezone.utc):
            raise ValueError("expires_at must be in the future")
        return self
