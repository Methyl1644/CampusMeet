from __future__ import annotations

import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.content import topic_to_dict
from services.identity import identity_summary
from storage.database.models import (
    Organization,
    OrganizationApplication,
    OrganizationMember,
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
