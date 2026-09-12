from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import identity as identity_api
from api.schemas.identity import OrganizationApplicationRequest, OrganizationReviewRequest
from storage.database.models import Organization, OrganizationApplication, OrganizationMember, User
from storage.database.shared.model import Base


def _user(email: str, *, role: str = "student") -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role=role,
    )


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add_all([_user("student@nju.edu.cn"), _user("operator@nju.edu.cn", role="operator")])
        session.commit()
    return factory


def _application() -> OrganizationApplicationRequest:
    return OrganizationApplicationRequest(
        organization_name="NJU Robotics Club",
        org_type="student_org",
        school_scope="Nanjing University",
        official_email="robotics@nju.edu.cn",
        official_page="https://example.nju.edu.cn/robotics",
        responsible_person_statement="I am the current responsible person for this organization.",
        evidence_reference="private/organization-evidence/robotics.pdf",
    )


def test_applicant_can_submit_and_view_status_without_private_evidence(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)

    created = identity_api.submit_organization_application(_application(), "1")
    listed = identity_api.my_organization_applications(1, 20, "1")

    assert created["data"]["status"] == "pending"
    assert listed["data"]["total"] == 1
    assert "evidence_reference" not in listed["data"]["list"][0]


def test_only_operator_can_read_private_application_detail(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    created = identity_api.submit_organization_application(_application(), "1")
    application_id = int(created["data"]["application_id"])

    with pytest.raises(HTTPException) as exc:
        identity_api.organization_application_detail(application_id, "1")
    assert exc.value.status_code == 403

    detail = identity_api.organization_application_detail(application_id, "2")
    assert detail["data"]["evidence_reference"].startswith("private/")


def test_approval_creates_verified_organization_and_initial_owner(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    application_id = int(
        identity_api.submit_organization_application(_application(), "1")["data"]["application_id"]
    )

    result = identity_api.review_organization_application(
        application_id,
        OrganizationReviewRequest(decision="approve", validity_days=365),
        "2",
    )

    assert result["data"]["status"] == "approved"
    with factory() as session:
        organization = session.execute(select(Organization)).scalar_one()
        owner = session.execute(select(OrganizationMember)).scalar_one()
        application = session.get(OrganizationApplication, application_id)
        assert organization.verification_status == "approved"
        assert owner.role == "owner" and owner.status == "active"
        assert owner.user_id == 1
        assert application.expires_at is not None


def test_rejection_records_reason_and_queue_is_paginated(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    application_id = int(
        identity_api.submit_organization_application(_application(), "1")["data"]["application_id"]
    )

    identity_api.review_organization_application(
        application_id,
        OrganizationReviewRequest(decision="reject", reason="Evidence is not current."),
        "2",
    )
    queue = identity_api.organization_application_queue("rejected", 1, 10, "2")

    assert queue["data"]["total"] == 1
    assert queue["data"]["page"] == 1
    with factory() as session:
        assert session.get(OrganizationApplication, application_id).review_reason == "Evidence is not current."
