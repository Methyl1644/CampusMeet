from __future__ import annotations

import datetime
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from services import moderation_cases
from storage.database.models import (
    AccountRestriction,
    AbuseEvent,
    Application,
    Conversation,
    Message,
    ModerationCase,
    ModerationEvent,
    PlatformRoleGrant,
    Post,
    User,
    UserBlock,
)
from storage.database.shared.model import Base
from api import posts as posts_api
from tools import application_tools, message_tools, post_tools


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        owner = User(
            id=1,
            email="owner@nju.edu.cn",
            password_hash="hash",
            nickname="owner",
            auth_status="verified",
        )
        applicant = User(
            id=2,
            email="applicant@nju.edu.cn",
            password_hash="hash",
            nickname="applicant",
            auth_status="verified",
        )
        operator = User(
            id=3,
            email="operator@nju.edu.cn",
            password_hash="hash",
            nickname="operator",
            auth_status="verified",
            site_role="senior_operator",
        )
        session.add_all([owner, applicant, operator])
        session.flush()
        post = Post(
            id=1,
            title="羽毛球招募",
            description="周末体育馆",
            main_category="体育与健身",
            activity_name="羽毛球",
            target_members=2,
            author_id=owner.id,
        )
        session.add(post)
        session.flush()
        session.add(
            Conversation(
                id=1,
                post_id=post.id,
                post_author_id=owner.id,
                applicant_id=applicant.id,
                status="active",
            )
        )
        session.commit()
    return factory


def test_user_block_prevents_application_without_persistence(monkeypatch):
    factory = _factory()
    with factory() as session:
        session.add(UserBlock(blocker_id=1, blocked_id=2))
        session.commit()
    monkeypatch.setattr(application_tools, "get_session", factory)

    result = json.loads(
        application_tools.create_application.invoke(
            {
                "user_id": "2",
                "post_id": "1",
                "role_wanted": "队员",
                "experience": "无",
                "available_time": "周末",
                "reason": "想参加活动",
                "questions": "",
            }
        )
    )

    assert result["success"] is False
    assert "屏蔽" in result["message"]
    with factory() as session:
        assert session.scalars(select(Application)).all() == []


def test_user_block_prevents_message_without_persistence(monkeypatch):
    factory = _factory()
    with factory() as session:
        session.add(UserBlock(blocker_id=1, blocked_id=2))
        session.commit()
    monkeypatch.setattr(message_tools, "get_session", factory)

    result = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "2", "conversation_id": "1", "content": "你好，想了解一下活动"}
        )
    )

    assert result["success"] is False
    assert "屏蔽" in result["message"]
    with factory() as session:
        assert session.scalars(select(Message)).all() == []


def test_active_posting_restriction_prevents_post_creation(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        case = ModerationCase(
            target_type="user",
            target_id="2",
            subject_user_id=2,
            status="resolved",
            priority="normal",
            reason_code="repeated_abuse",
        )
        session.add(case)
        session.flush()
        session.add(
            AccountRestriction(
                case_id=case.id,
                user_id=2,
                restriction_type="posting",
                reason_code="repeated_abuse",
                starts_at=now - datetime.timedelta(minutes=1),
                expires_at=now + datetime.timedelta(hours=1),
                created_by=3,
            )
        )
        session.commit()
    monkeypatch.setattr(post_tools, "get_session", factory)

    result = json.loads(
        post_tools.create_post.invoke(
            {
                "user_id": "2",
                "title": "正常组队",
                "description": "周末一起打球",
                "main_category": "体育与健身",
                "activity_name": "羽毛球",
                "target_members": 2,
                "needed_roles": "队员",
            }
        )
    )

    assert result["success"] is False
    assert "限制" in result["message"]
    with factory() as session:
        assert session.scalar(select(Post).where(Post.author_id == 2)) is None


def test_governed_platform_roles_ignore_stale_site_role():
    factory = _factory()
    with factory() as session:
        stale_operator = session.get(User, 3)
        session.add(
            PlatformRoleGrant(
                user_id=1,
                role="senior_operator",
                status="active",
                granted_by=1,
                accepted_at=datetime.datetime.now(datetime.timezone.utc),
                effective_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        session.commit()

        with pytest.raises(PermissionError):
            moderation_cases.list_cases(session, stale_operator, page=1, page_size=20)


def test_posting_restriction_prevents_post_update(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        case = ModerationCase(
            target_type="user",
            target_id="1",
            subject_user_id=1,
            status="resolved",
            priority="normal",
            reason_code="repeated_abuse",
        )
        session.add(case)
        session.flush()
        session.add(
            AccountRestriction(
                case_id=case.id,
                user_id=1,
                restriction_type="posting",
                reason_code="repeated_abuse",
                starts_at=now - datetime.timedelta(minutes=1),
                expires_at=now + datetime.timedelta(hours=1),
                created_by=3,
            )
        )
        session.commit()
    monkeypatch.setattr(posts_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        posts_api.update(1, {"title": "新标题"}, "1")

    assert exc.value.status_code == 403
    assert "限制" in str(exc.value.detail)
    with factory() as session:
        assert session.get(Post, 1).title == "羽毛球招募"


def test_rejected_message_records_only_a_masked_moderation_event(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(message_tools, "get_session", factory)

    result = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "2", "conversation_id": "1", "content": "联系手机 13800138000"}
        )
    )

    assert result["success"] is False
    with factory() as session:
        event = session.scalars(select(ModerationEvent)).one()
        assert event.action == "revise"
        assert event.surface == "message"
        assert "13800138000" not in event.excerpt
        assert session.scalars(select(Message)).all() == []


def test_rapid_applications_are_rejected_at_the_write_boundary(monkeypatch):
    factory = _factory()
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        session.add_all(
            AbuseEvent(
                user_id=2,
                event_type="application",
                target_id=f"post:{index + 10}",
                outcome="allow",
                created_at=now - datetime.timedelta(seconds=index),
            )
            for index in range(8)
        )
        session.commit()
    monkeypatch.setattr(application_tools, "get_session", factory)

    result = json.loads(
        application_tools.create_application.invoke(
            {
                "user_id": "2",
                "post_id": "1",
                "role_wanted": "队员",
                "experience": "无",
                "available_time": "周末",
                "reason": "想参加活动",
                "questions": "",
            }
        )
    )

    assert result["success"] is False
    assert "频繁" in result["message"]
    assert result["retry_after_seconds"] > 0


def test_repeated_messages_are_rejected_at_the_write_boundary(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(message_tools, "get_session", factory)
    payload = {"user_id": "2", "conversation_id": "1", "content": "同一条正常消息"}

    results = [json.loads(message_tools.send_message.invoke(payload)) for _ in range(4)]

    assert all(item["success"] is True for item in results[:3])
    assert results[3]["success"] is False
    assert "频繁" in results[3]["message"]
    with factory() as session:
        assert len(session.scalars(select(Message)).all()) == 3
