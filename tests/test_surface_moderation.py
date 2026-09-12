from __future__ import annotations

import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import content as content_api
from api import posts as posts_api
from storage.database.models import Application, Conversation, Message, Post, Tag, Topic, User
from storage.database.shared.model import Base
from tools import application_tools, message_tools


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add_all(
        [
            User(
                id=1,
                email="owner@nju.edu.cn",
                password_hash="x",
                nickname="owner",
                auth_status="verified",
                site_role="operator",
            ),
            User(id=2, email="member@nju.edu.cn", password_hash="x", nickname="member", auth_status="verified"),
            Tag(
                id="activity_badminton",
                canonical_name="羽毛球",
                category="activity",
                display_color="green",
            ),
            Topic(
                id=1,
                channel="official",
                title="羽毛球活动",
                short_title="羽毛球",
                organizer="CampusMate",
                organizer_key="campusmate",
                canonical_event_key="badminton",
                edition="2026",
                summary="校内活动",
                content="公开体育活动",
                created_by=1,
            ),
            Post(
                id=1,
                title="羽毛球招募",
                description="周末体育馆",
                main_category="体育与健身",
                activity_name="羽毛球",
                target_members=2,
                author_id=1,
            ),
            Conversation(id=1, post_id=1, post_author_id=1, applicant_id=2, status="active"),
        ]
    )
    session.commit()
    session.close()
    return factory


def test_private_dating_post_is_blocked_before_ai_review(monkeypatch):
    monkeypatch.setattr(
        posts_api,
        "_classification_review",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("AI must not review a deterministic block")),
    )

    try:
        posts_api.create(
            {
                "title": "酒店约会",
                "description": "约女同学去宾馆房间单独见面",
                "activity_name": "约会",
                "target_members": 2,
            },
            "1",
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
        assert "高风险" in str(getattr(exc, "detail", ""))
    else:
        raise AssertionError("unsafe post was accepted")


def test_topic_publish_and_update_use_the_same_moderation_policy(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(content_api, "get_session", factory)

    unsafe = {
        "channel": "official",
        "title": "酒店约会",
        "short_title": "约会",
        "organizer": "CampusMate",
        "edition": "2027",
        "summary": "约同学去酒店房间单独见面",
        "content": "私密活动",
        "tag_ids": ["activity_badminton"],
    }
    try:
        content_api.publish_topic(unsafe, "1")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("unsafe topic was accepted")

    try:
        content_api.update_topic(1, {"content": "约女同学去宾馆房间单独见面"}, "1")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("unsafe topic update was accepted")

    session = factory()
    assert session.get(Topic, 1).content == "公开体育活动"
    assert session.execute(select(Topic)).scalars().all() == [session.get(Topic, 1)]
    session.close()


def test_application_text_is_moderated_before_persistence(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(application_tools, "get_session", factory)

    result = json.loads(
        application_tools.create_application.invoke(
            {
                "user_id": "2",
                "post_id": "1",
                "role_wanted": "队员",
                "experience": "无",
                "available_time": "周末",
                "reason": "加微信 abc_12345 后再说",
                "questions": "",
            }
        )
    )

    assert result["success"] is False
    assert result["moderation"]["action"] == "revise"
    session = factory()
    assert session.execute(select(Application)).scalars().all() == []
    session.close()


def test_contact_is_blocked_before_confirmation_and_allowed_after_unlock(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(message_tools, "get_session", factory)

    blocked = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "2", "conversation_id": "1", "content": "手机号 13800138000"}
        )
    )
    assert blocked["success"] is False
    assert blocked["moderation"]["action"] == "revise"

    session = factory()
    conversation = session.get(Conversation, 1)
    conversation.contact_unlocked = True
    session.commit()
    session.close()

    allowed = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "2", "conversation_id": "1", "content": "手机号 13800138000"}
        )
    )
    assert allowed["success"] is True

    session = factory()
    assert [message.content for message in session.execute(select(Message)).scalars()] == ["手机号 13800138000"]
    session.close()


def test_critical_threat_is_blocked_even_after_contact_unlock(monkeypatch):
    factory = _factory()
    session = factory()
    session.get(Conversation, 1).contact_unlocked = True
    session.commit()
    session.close()
    monkeypatch.setattr(message_tools, "get_session", factory)

    result = json.loads(
        message_tools.send_message.invoke(
            {"user_id": "1", "conversation_id": "1", "content": "不答应我就打断你的腿"}
        )
    )

    assert result["success"] is False
    assert result["moderation"]["action"] == "block"
    session = factory()
    assert session.execute(select(Message)).scalars().all() == []
    session.close()
