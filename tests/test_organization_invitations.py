from __future__ import annotations

import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import identity as identity_api
from api.schemas.identity import OrganizationInvitationRequest
from storage.database.models import Organization, OrganizationInvitation, OrganizationMember, User
from storage.database.shared.model import Base


def _factory(*, organization_expired: bool = False):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        owner = User(
            email="owner@nju.edu.cn",
            password_hash="hash",
            nickname="owner",
            auth_status="verified",
        )
        invitee = User(
            email="invitee@nju.edu.cn",
            password_hash="hash",
            nickname="invitee",
            auth_status="verified",
        )
        session.add_all([owner, invitee])
        session.flush()
        organization = Organization(
            name="NJU Robotics Club",
            org_type="student_org",
            verification_status="approved",
            verified_at=datetime.datetime.now(datetime.timezone.utc),
            expires_at=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=-1 if organization_expired else 365),
        )
        session.add(organization)
        session.flush()
        session.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
                expires_at=organization.expires_at,
            )
        )
        session.commit()
    return factory


def test_invitation_requires_acceptance_before_membership_becomes_active(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    request = OrganizationInvitationRequest(user_id=2, role="publisher")

    invited = identity_api.invite_organization_member(1, request, "1")
    invitation_id = int(invited["data"]["invitation_id"])
    with factory() as session:
        assert session.execute(select(OrganizationMember).where(OrganizationMember.user_id == 2)).first() is None

    accepted = identity_api.accept_organization_invitation(invitation_id, "2")
    assert accepted["data"]["status"] == "accepted"
    with factory() as session:
        member = session.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == 2)
        ).scalar_one()
        assert member.role == "publisher" and member.status == "active"


def test_invitee_can_decline_without_receiving_membership(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    invitation_id = int(
        identity_api.invite_organization_member(
            1, OrganizationInvitationRequest(user_id=2, role="member"), "1"
        )["data"]["invitation_id"]
    )

    declined = identity_api.decline_organization_invitation(invitation_id, "2")
    assert declined["data"]["status"] == "declined"
    with factory() as session:
        assert session.execute(select(OrganizationMember).where(OrganizationMember.user_id == 2)).first() is None


def test_expired_organization_cannot_invite_members(monkeypatch):
    factory = _factory(organization_expired=True)
    monkeypatch.setattr(identity_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        identity_api.invite_organization_member(
            1, OrganizationInvitationRequest(user_id=2, role="member"), "1"
        )
    assert exc.value.status_code == 409


def test_owner_can_revoke_member_but_not_the_last_owner(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    invitation_id = int(
        identity_api.invite_organization_member(
            1, OrganizationInvitationRequest(user_id=2, role="member"), "1"
        )["data"]["invitation_id"]
    )
    identity_api.accept_organization_invitation(invitation_id, "2")

    revoked = identity_api.revoke_organization_member(1, 2, "1")
    assert revoked["data"]["status"] == "revoked"

    with pytest.raises(HTTPException) as exc:
        identity_api.revoke_organization_member(1, 1, "1")
    assert exc.value.status_code == 409
