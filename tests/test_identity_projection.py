from __future__ import annotations

import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api import auth as auth_api
from services.content import topic_to_dict
from services.identity import identity_summary, managed_organizations
from storage.database.models import (
    Organization,
    OrganizationApplication,
    OrganizationMember,
    PlatformRoleGrant,
    Post,
    PostCollaborator,
    Topic,
    TopicCollaborator,
    User,
)
from storage.database.shared.model import Base
from tools.post_tools import _post_to_dict


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_identity_summary_includes_only_active_scoped_roles():
    now = datetime.datetime.now(datetime.timezone.utc)
    with _session() as session:
        owner = User(
            email="owner@nju.edu.cn",
            password_hash="hash",
            nickname="owner",
            auth_status="verified",
        )
        expired = User(
            email="expired@nju.edu.cn",
            password_hash="hash",
            nickname="expired",
            auth_status="verified",
        )
        session.add_all([owner, expired])
        session.flush()
        organization = Organization(
            name="NJU Robotics Club",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=90),
        )
        session.add(organization)
        session.flush()
        session.add_all(
            [
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                    expires_at=organization.expires_at,
                ),
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=expired.id,
                    role="publisher",
                    status="active",
                    expires_at=now - datetime.timedelta(days=1),
                ),
            ]
        )
        topic = Topic(
            channel="organization",
            title="Robotics Contest",
            short_title="Robotics",
            organizer="NJU Robotics Club",
            organizer_key="nju robotics club",
            canonical_event_key="robotics",
            edition="2026",
            summary="summary",
            content="content",
            organization_id=organization.id,
            created_by=owner.id,
        )
        post = Post(
            title="Recruit teammates",
            description="Build a robot",
            main_category="竞赛与项目",
            activity_name="Robotics Contest",
            target_members=3,
            author_id=expired.id,
        )
        session.add_all([topic, post])
        session.flush()
        session.add_all(
            [
                TopicCollaborator(
                    topic_id=topic.id,
                    user_id=owner.id,
                    role="manager",
                    status="active",
                    granted_by=owner.id,
                    expires_at=now + datetime.timedelta(days=30),
                ),
                PostCollaborator(
                    post_id=post.id,
                    user_id=owner.id,
                    role="editor",
                    status="active",
                    granted_by=expired.id,
                    expires_at=now + datetime.timedelta(days=30),
                ),
            ]
        )
        session.flush()

        summary = identity_summary(session, owner)
        expired_summary = identity_summary(session, expired)

        assert summary["campus_verified"] is True
        assert summary["organization_roles"][0]["role"] == "owner"
        assert summary["topic_roles"][0]["role"] == "manager"
        assert summary["post_roles"][0]["role"] == "editor"
        assert expired_summary["organization_roles"] == []
        assert "evidence" not in repr(summary).lower()
        public_post = _post_to_dict(post, expired, session)
        assert public_post["collaborators"] == [
            {
                "user_id": str(owner.id),
                "nickname": "owner",
                "role": "editor",
                "badge": "帖子协作者",
            }
        ]


def test_identity_summary_exposes_highest_active_platform_role():
    with _session() as session:
        user = User(
            email="operator@nju.edu.cn",
            password_hash="hash",
            nickname="operator",
            auth_status="verified",
        )
        session.add(user)
        session.flush()
        session.add_all(
            [
                PlatformRoleGrant(
                    user_id=user.id,
                    role="operator",
                    status="active",
                    granted_by=user.id,
                ),
                PlatformRoleGrant(
                    user_id=user.id,
                    role="senior_operator",
                    status="active",
                    granted_by=user.id,
                ),
            ]
        )
        session.flush()

        summary = identity_summary(session, user)

        assert summary["platform_role"] == "senior_operator"


def test_auth_success_includes_management_identity(monkeypatch):
    session = _session()
    user = User(
        email="login-operator@nju.edu.cn",
        password_hash="hash",
        nickname="login operator",
        auth_status="verified",
        site_role="operator",
    )
    session.add(user)
    session.flush()
    monkeypatch.setattr(auth_api, "get_session", lambda: session)

    result = auth_api._auth_success(
        {"token": "token", "user": {"id": str(user.id), "nickname": user.nickname}},
        "ok",
    )

    assert result["data"]["user"]["identity"]["platform_role"] == "operator"


def test_public_topic_projection_exposes_badges_but_not_private_evidence():
    now = datetime.datetime.now(datetime.timezone.utc)
    with _session() as session:
        owner = User(
            email="private-owner@nju.edu.cn",
            phone="13800138000",
            wechat="private_wechat",
            password_hash="hash",
            nickname="Club Owner",
            auth_status="verified",
        )
        session.add(owner)
        session.flush()
        organization = Organization(
            name="NJU Robotics Club",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=90),
        )
        session.add(organization)
        session.flush()
        session.add(
            OrganizationApplication(
                applicant_id=owner.id,
                organization_name=organization.name,
                org_type=organization.org_type,
                evidence="private evidence",
                evidence_reference="private/evidence.pdf",
                review_reason="operator note",
                status="approved",
            )
        )
        topic = Topic(
            channel="organization",
            title="Robotics Contest",
            short_title="Robotics",
            organizer=organization.name,
            organizer_key="nju robotics club",
            canonical_event_key="robotics",
            edition="2026",
            summary="summary",
            content="content",
            organization_id=organization.id,
            created_by=owner.id,
        )
        session.add(topic)
        session.flush()
        session.add(
            TopicCollaborator(
                topic_id=topic.id,
                user_id=owner.id,
                role="manager",
                status="active",
                granted_by=owner.id,
                expires_at=now + datetime.timedelta(days=30),
            )
        )
        session.flush()

        public = topic_to_dict(session, topic)
        serialized = repr(public).lower()

        assert {badge["kind"] for badge in public["trust_badges"]} == {"verified_organization"}
        assert public["responsible_people"] == [
            {"user_id": str(owner.id), "nickname": "Club Owner", "role": "manager", "badge": "活动负责人"}
        ]
        assert "private/evidence" not in serialized
        assert "operator note" not in serialized
        assert "13800138000" not in serialized
        assert "private_wechat" not in serialized


def test_public_topic_projection_labels_collaborator_levels():
    now = datetime.datetime.now(datetime.timezone.utc)
    with _session() as session:
        users = [
            User(email=f"role-{index}@nju.edu.cn", password_hash="hash", nickname=f"role-{index}", auth_status="verified")
            for index in range(3)
        ]
        session.add_all(users)
        session.flush()
        topic = Topic(
            channel="official",
            title="Role Labels",
            short_title="Roles",
            organizer="CampusMate",
            organizer_key="campusmate",
            canonical_event_key="role-labels",
            edition="2026",
            summary="summary",
            content="content",
            created_by=users[0].id,
        )
        session.add(topic)
        session.flush()
        session.add_all([
            TopicCollaborator(topic_id=topic.id, user_id=user.id, role=role, status="active", granted_by=users[0].id, expires_at=now + datetime.timedelta(days=30))
            for user, role in zip(users, ("manager", "editor", "coordinator"), strict=True)
        ])
        session.flush()

        badges = {person["role"]: person["badge"] for person in topic_to_dict(session, topic)["responsible_people"]}

        assert badges == {
            "manager": "活动负责人",
            "editor": "活动组织者",
            "coordinator": "活动协作成员",
        }


def test_managed_organizations_returns_only_active_owner_memberships():
    now = datetime.datetime.now(datetime.timezone.utc)
    with _session() as session:
        user = User(
            email="manager@nju.edu.cn",
            password_hash="hash",
            nickname="manager",
            auth_status="verified",
        )
        session.add(user)
        session.flush()
        owned = Organization(
            name="Owned Organization",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=30),
        )
        published = Organization(
            name="Publisher Organization",
            org_type="student_org",
            verification_status="approved",
            expires_at=now + datetime.timedelta(days=30),
        )
        expired = Organization(
            name="Expired Organization",
            org_type="student_org",
            verification_status="approved",
            expires_at=now - datetime.timedelta(days=1),
        )
        session.add_all([owned, published, expired])
        session.flush()
        session.add_all(
            [
                OrganizationMember(
                    organization_id=owned.id,
                    user_id=user.id,
                    role="owner",
                    status="active",
                    expires_at=owned.expires_at,
                ),
                OrganizationMember(
                    organization_id=published.id,
                    user_id=user.id,
                    role="publisher",
                    status="active",
                    expires_at=published.expires_at,
                ),
                OrganizationMember(
                    organization_id=expired.id,
                    user_id=user.id,
                    role="owner",
                    status="active",
                    expires_at=expired.expires_at,
                ),
            ]
        )
        session.flush()

        result = managed_organizations(session, user)

        assert len(result) == 1
        assert result[0]["organization_id"] == str(owned.id)
        assert result[0]["organization_name"] == "Owned Organization"
        assert result[0]["role"] == "owner"
        assert result[0]["expires_at"] is not None
