from __future__ import annotations

import datetime
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services import identity, moderation_cases, notifications
from storage.database.models import (
    Appeal,
    Conversation,
    ModerationCase,
    Notification,
    Organization,
    OrganizationApplication,
    OrganizationMember,
    Post,
    User,
)
from storage.database.shared.model import Base
from tools import application_tools, message_tools


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(id=1, email="owner@nju.edu.cn", password_hash="x", nickname="owner", auth_status="verified"),
                User(id=2, email="applicant@nju.edu.cn", password_hash="x", nickname="applicant", auth_status="verified"),
            ]
        )
        session.add(
            Post(
                id=1,
                title="羽毛球招募",
                description="周末体育馆",
                main_category="体育与健身",
                activity_name="羽毛球",
                target_members=3,
                author_id=1,
            )
        )
        session.commit()
    return factory


def test_notification_dedupe_pagination_and_read_lifecycle():
    factory = _factory()
    with factory() as session:
        first = notifications.notify(
            session,
            user_id=1,
            event_type="application.created",
            title="收到新申请",
            body="有同学申请加入",
            target_type="post",
            target_id="1",
            dedupe_key="application:9:created",
        )
        second = notifications.notify(
            session,
            user_id=1,
            event_type="application.created",
            title="收到新申请",
            body="重试不应重复通知",
            target_type="post",
            target_id="1",
            dedupe_key="application:9:created",
        )
        session.commit()
        assert first.id == second.id

        items, total = notifications.list_notifications(session, 1, page=1, page_size=10)
        assert total == 1
        assert items[0].read_at is None
        assert notifications.unread_count(session, 1) == 1
        notifications.mark_read(session, 1, first.id)
        session.commit()
        assert notifications.unread_count(session, 1) == 0


def test_application_creation_notifies_post_owner_in_same_transaction(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(application_tools, "get_session", factory)

    result = json.loads(
        application_tools.create_application.invoke(
            {
                "user_id": "2",
                "post_id": "1",
                "role_wanted": "队员",
                "experience": "有经验",
                "available_time": "周末",
                "reason": "想参加活动",
                "questions": "",
            }
        )
    )

    assert result["success"] is True
    with factory() as session:
        item = session.query(Notification).one()
        assert item.user_id == 1
        assert item.event_type == "application.created"


def test_message_notifies_the_other_conversation_participant(monkeypatch):
    factory = _factory()
    with factory() as session:
        session.add(
            Conversation(
                id=1,
                post_id=1,
                post_author_id=1,
                applicant_id=2,
                status="active",
            )
        )
        session.commit()
    monkeypatch.setattr(message_tools, "get_session", factory)

    result = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "2", "conversation_id": "1", "content": "你好，可以聊聊组队吗？"}
        )
    )

    assert result["success"] is True
    with factory() as session:
        item = session.query(Notification).one()
        assert item.user_id == 1
        assert item.event_type == "message.created"
        assert item.target_type == "conversation"


def test_identity_invitation_and_review_results_create_notifications():
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        owner = session.get(User, 1)
        invitee = session.get(User, 2)
        operator = User(
            id=3,
            email="operator@nju.edu.cn",
            password_hash="x",
            nickname="operator",
            auth_status="verified",
            site_role="operator",
        )
        organization = Organization(
            id=1,
            name="南京大学测试社团",
            org_type="student_org",
            verification_status="approved",
            verified_at=now,
            expires_at=now + datetime.timedelta(days=365),
        )
        session.add_all([operator, organization])
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
        application = OrganizationApplication(
            applicant_id=invitee.id,
            organization_name="南京大学新社团",
            org_type="student_org",
            school_scope="南京大学",
            responsible_person_statement="负责人说明",
            evidence="evidence",
            status="pending",
        )
        session.add(application)
        session.flush()

        invitation = identity.create_invitation(
            session,
            owner,
            organization,
            invitee,
            role="publisher",
            expires_at=None,
        )
        identity.review_application(
            session,
            operator,
            application,
            decision="approve",
            reason="材料完整",
            validity_days=365,
        )
        session.commit()

        events = {item.event_type: item for item in session.query(Notification).all()}
        assert events["organization.invitation.created"].user_id == invitee.id
        assert events["organization.application.approved"].user_id == invitee.id
        assert events["organization.invitation.created"].target_id == str(invitation.id)


def test_appeal_review_notifies_appellant():
    factory = _factory()
    with factory() as session:
        operator = User(
            id=3,
            email="operator@nju.edu.cn",
            password_hash="x",
            nickname="operator",
            auth_status="verified",
            site_role="operator",
        )
        case = ModerationCase(
            id=1,
            target_type="user",
            target_id="2",
            subject_user_id=2,
            status="resolved",
            priority="normal",
            reason_code="policy.violation",
        )
        appeal = Appeal(
            id=1,
            case_id=1,
            appellant_id=2,
            statement="申请复核",
            status="pending",
        )
        session.add_all([operator, case, appeal])
        session.flush()

        moderation_cases.review_appeal(
            session,
            operator,
            appeal,
            outcome="rejected",
            resolution="维持原处理",
        )
        session.commit()

        item = session.query(Notification).one()
        assert item.user_id == 2
        assert item.event_type == "moderation.appeal.rejected"
