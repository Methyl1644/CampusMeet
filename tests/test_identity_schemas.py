from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from api.schemas.identity import (
    OrganizationApplicationRequest,
    OrganizationInvitationRequest,
    OrganizationReviewRequest,
)


def test_organization_application_requires_private_evidence_reference():
    with pytest.raises(ValidationError):
        OrganizationApplicationRequest(
            organization_name="Student Union",
            org_type="student_org",
            school_scope="university",
            responsible_person_statement="I am the current responsible person.",
        )


def test_organization_rejection_requires_reason():
    with pytest.raises(ValidationError):
        OrganizationReviewRequest(decision="reject", reason="")
    assert OrganizationReviewRequest(decision="approve").decision == "approve"


def test_organization_invitation_rejects_owner_role_and_past_expiry():
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    with pytest.raises(ValidationError):
        OrganizationInvitationRequest(user_id=2, role="owner", expires_at=future)
    with pytest.raises(ValidationError):
        OrganizationInvitationRequest(
            user_id=2,
            role="member",
            expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1),
        )
