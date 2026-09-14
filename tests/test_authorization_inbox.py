from __future__ import annotations

import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import identity as identity_api
from api import operators as operators_api
from api import permissions as permissions_api
from storage.database.models import (
    Organization,
    OrganizationInvitation,
    OrganizationOwnershipTransfer,
    PlatformRoleGrant,
    Topic,
    TopicCollaborator,
    User,
)
from storage.database.shared.model import Base


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add_all(
            [
                User(email="inviter@nju.edu.cn", password_hash="hash", nickname="inviter", auth_status="verified"),
                User(email="invitee@nju.edu.cn", password_hash="hash", nickname="invitee", auth_status="verified"),
                User(email="other@nju.edu.cn", password_hash="hash", nickname="other", auth_status="verified"),
            ]
        )
        session.commit()
    return factory


def test_invitee_lists_and_declines_own_topic_collaboration(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        topic = Topic(
            channel="official",
            title="挑战杯",
            short_title="挑战杯",
            organizer="CampusMate",
            organizer_key="campusmate",
            canonical_event_key="challenge-cup",
            edition="2026",
            summary="summary",
            content="content",
            created_by=1,
        )
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicCollaborator(topic_id=topic.id, user_id=2, role="editor", status="pending", granted_by=1, expires_at=now + datetime.timedelta(days=30)),
                TopicCollaborator(topic_id=topic.id, user_id=3, role="manager", status="pending", granted_by=1, expires_at=now + datetime.timedelta(days=30)),
            ]
        )
        session.commit()
        topic_id = topic.id
    monkeypatch.setattr(permissions_api, "get_session", factory)

    inbox = permissions_api.my_topic_collaborations("pending", 1, 20, "2")

    assert inbox["data"]["total"] == 1
    assert inbox["data"]["list"][0]["topic_title"] == "挑战杯"
    declined = permissions_api.decline_topic_collaboration(topic_id, "2")
    assert declined["data"]["status"] == "revoked"

    with pytest.raises(HTTPException) as exc:
        permissions_api.decline_topic_collaboration(topic_id, "2")
    assert exc.value.status_code == 404


def test_topic_collaboration_accept_response_includes_topic_title(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        topic = Topic(
            channel="official",
            title="创新创业训练",
            short_title="创新训练",
            organizer="CampusMate",
            organizer_key="campusmate",
            canonical_event_key="innovation-training",
            edition="2026",
            summary="summary",
            content="content",
            created_by=1,
        )
        session.add(topic)
        session.flush()
        session.add(TopicCollaborator(topic_id=topic.id, user_id=2, role="editor", status="pending", granted_by=1, expires_at=now + datetime.timedelta(days=30)))
        session.commit()
        topic_id = topic.id
    monkeypatch.setattr(permissions_api, "get_session", factory)

    accepted = permissions_api.accept_topic_collaboration(topic_id, "2")

    assert accepted["data"]["topic_title"] == "创新创业训练"


def test_invitee_can_decline_own_pending_platform_role(monkeypatch):
    factory = _factory()
    with factory() as session:
        grant = PlatformRoleGrant(user_id=2, role="operator", status="pending", granted_by=1)
        session.add(grant)
        session.commit()
        grant_id = grant.id
    monkeypatch.setattr(operators_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        operators_api.decline_platform_role(grant_id, "3")
    assert exc.value.status_code == 403

    declined = operators_api.decline_platform_role(grant_id, "2")

    assert declined["data"]["status"] == "revoked"

    with pytest.raises(HTTPException) as exc:
        operators_api.decline_platform_role(grant_id, "2")
    assert exc.value.status_code == 409


def test_successor_can_decline_ownership_transfer(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        organization = Organization(
            name="校科协",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=90),
        )
        session.add(organization)
        session.flush()
        transfer = OrganizationOwnershipTransfer(
            organization_id=organization.id,
            from_owner_id=1,
            to_owner_id=2,
            initiated_by=1,
            status="pending",
            expires_at=now + datetime.timedelta(days=7),
        )
        session.add(transfer)
        session.commit()
        transfer_id = transfer.id
    monkeypatch.setattr(identity_api, "get_session", factory)

    inbox = identity_api.my_organization_ownership_transfers(1, 20, "2")
    assert inbox["data"]["list"][0]["organization_name"] == "校科协"
    with pytest.raises(HTTPException) as exc:
        identity_api.decline_organization_ownership_transfer(transfer_id, "3")
    assert exc.value.status_code == 403
    declined = identity_api.decline_organization_ownership_transfer(transfer_id, "2")

    assert declined["data"]["status"] == "declined"

    with pytest.raises(HTTPException) as exc:
        identity_api.decline_organization_ownership_transfer(transfer_id, "2")
    assert exc.value.status_code == 409


def test_organization_invitation_inbox_includes_organization_name(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        organization = Organization(
            name="学生会",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=90),
        )
        session.add(organization)
        session.flush()
        session.add(
            OrganizationInvitation(
                organization_id=organization.id,
                inviter_id=1,
                invitee_id=2,
                requested_role="publisher",
                status="pending",
                expires_at=now + datetime.timedelta(days=7),
            )
        )
        session.commit()
    monkeypatch.setattr(identity_api, "get_session", factory)

    inbox = identity_api.my_organization_invitations(1, 20, "2")

    assert inbox["data"]["list"][0]["organization_name"] == "学生会"


def test_authorization_inboxes_filter_pending_before_pagination(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        organization = Organization(
            name="青年志愿者协会",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=90),
        )
        session.add(organization)
        session.flush()
        session.add_all(
            [
                PlatformRoleGrant(user_id=2, role="operator", status="revoked", granted_by=1),
                PlatformRoleGrant(user_id=2, role="operator", status="pending", granted_by=1),
                OrganizationInvitation(organization_id=organization.id, inviter_id=1, invitee_id=2, requested_role="member", status="declined", expires_at=now + datetime.timedelta(days=7)),
                OrganizationInvitation(organization_id=organization.id, inviter_id=1, invitee_id=2, requested_role="publisher", status="pending", expires_at=now + datetime.timedelta(days=7)),
                OrganizationOwnershipTransfer(organization_id=organization.id, from_owner_id=1, to_owner_id=2, initiated_by=1, status="declined", expires_at=now + datetime.timedelta(days=7)),
                OrganizationOwnershipTransfer(organization_id=organization.id, from_owner_id=1, to_owner_id=2, initiated_by=1, status="pending", expires_at=now + datetime.timedelta(days=7)),
            ]
        )
        session.commit()
    monkeypatch.setattr(operators_api, "get_session", factory)
    monkeypatch.setattr(identity_api, "get_session", factory)

    roles = operators_api.my_platform_roles(page=1, page_size=20, user_id="2", status="pending")
    invitations = identity_api.my_organization_invitations(page=1, page_size=20, user_id="2", status="pending")
    transfers = identity_api.my_organization_ownership_transfers(page=1, page_size=20, user_id="2", status="pending")

    assert roles["data"]["total"] == 1
    assert invitations["data"]["total"] == 1
    assert transfers["data"]["total"] == 1
