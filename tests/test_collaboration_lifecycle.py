from __future__ import annotations

import datetime
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import applications as applications_api
from api import content as content_api
from api import posts as posts_api
from jobs.maintenance import run_maintenance
from services.participation import deadline_has_passed
from storage.database.models import Application, AuditLog, Conversation, Post, Topic, User
from storage.database.shared.model import Base
from tools import application_tools
from tools import post_tools


def _factory(*, deadline: str = "", current_members: int = 1, target_members: int = 3):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(
                    id=1,
                    email="owner@nju.edu.cn",
                    password_hash="hash",
                    nickname="owner",
                    auth_status="verified",
                ),
                User(
                    id=2,
                    email="applicant@nju.edu.cn",
                    password_hash="hash",
                    nickname="applicant",
                    auth_status="verified",
                ),
            ]
        )
        session.add(
            Post(
                id=1,
                title="校园组队",
                description="正常活动",
                main_category="校园生活",
                activity_name="校园活动",
                current_members=current_members,
                target_members=target_members,
                deadline=deadline,
                author_id=1,
            )
        )
        session.commit()
    return factory


def _application_payload() -> dict[str, str]:
    return {
        "user_id": "2",
        "post_id": "1",
        "role_wanted": "队员",
        "experience": "有经验",
        "available_time": "周末",
        "reason": "想参加活动",
        "questions": "",
    }


def test_full_or_expired_post_rejects_new_application(monkeypatch):
    full_factory = _factory(current_members=3, target_members=3)
    monkeypatch.setattr(application_tools, "get_session", full_factory)
    full = json.loads(application_tools.create_application.invoke(_application_payload()))
    assert full["success"] is False
    assert "已满" in full["message"]

    expired_factory = _factory(
        deadline=(datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    )
    monkeypatch.setattr(application_tools, "get_session", expired_factory)
    expired = json.loads(application_tools.create_application.invoke(_application_payload()))
    assert expired["success"] is False
    assert "截止" in expired["message"]
    with expired_factory() as session:
        assert session.scalars(select(Application)).all() == []


@pytest.mark.parametrize(
    "deadline",
    [
        "明天下午截止",
        "next Friday",
        "2026-09-13T12:30:00",
        "2026-02-30",
    ],
)
def test_unknown_legacy_deadlines_remain_open_for_maintenance_reopen_and_join(
    monkeypatch,
    deadline,
):
    factory = _factory(deadline=deadline)
    now = datetime.datetime(2026, 9, 13, 12, tzinfo=datetime.timezone.utc)

    with factory() as session:
        post = session.get(Post, 1)
        assert post.deadline_at is None
        assert deadline_has_passed(post, now=now) is False
        maintenance = run_maintenance(session, now=now)
        assert maintenance["posts_closed"] == 0
        assert post.status == "recruiting"
        post.status = "closed"
        session.commit()

    monkeypatch.setattr(posts_api, "get_session", factory)
    assert posts_api.reopen_post(1, "1")["data"]["status"] == "recruiting"

    monkeypatch.setattr(application_tools, "get_session", factory)
    joined = json.loads(
        application_tools.create_application.invoke(_application_payload())
    )
    assert joined["success"] is True


def test_pending_application_can_be_withdrawn_and_transition_is_audited(monkeypatch):
    factory = _factory()
    with factory() as session:
        app = Application(
            post_id=1,
            applicant_id=2,
            role_wanted="队员",
            experience="有经验",
            available_time="周末",
            reason="想参加",
            status="pending",
        )
        session.add(app)
        session.commit()
        app_id = app.id
    monkeypatch.setattr(application_tools, "get_session", factory)

    result = applications_api.withdraw(str(app_id), "2")

    assert result["data"]["withdrawn"] is True
    with factory() as session:
        stored = session.get(Application, app_id)
        assert stored.status == "withdrawn"
        assert stored.withdrawn_at is not None
        assert session.scalar(
            select(AuditLog).where(AuditLog.action == "application.withdraw")
        ) is not None


def test_accept_application_is_idempotent_and_reuses_conversation(monkeypatch):
    factory = _factory()
    with factory() as session:
        app = Application(
            post_id=1,
            applicant_id=2,
            role_wanted="队员",
            experience="有经验",
            available_time="周末",
            reason="想参加",
            status="pending",
        )
        session.add(app)
        session.commit()
        app_id = str(app.id)
    monkeypatch.setattr(application_tools, "get_session", factory)

    first = json.loads(
        application_tools.accept_application.invoke({"user_id": "1", "application_id": app_id})
    )
    second = json.loads(
        application_tools.accept_application.invoke({"user_id": "1", "application_id": app_id})
    )

    assert first["success"] is True
    assert second["success"] is True
    assert second["conversation_id"] == first["conversation_id"]
    with factory() as session:
        assert session.query(Conversation).count() == 1


def test_post_owner_can_close_reopen_archive_and_soft_delete(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(posts_api, "get_session", factory)

    assert posts_api.close_post(1, "1")["data"]["status"] == "closed"
    assert posts_api.reopen_post(1, "1")["data"]["status"] == "recruiting"
    assert posts_api.archive_post(1, "1")["data"]["status"] == "archived"
    assert posts_api.delete_post(1, "1")["data"]["status"] == "deleted"

    with factory() as session:
        post = session.get(Post, 1)
        assert post.closed_at is not None
        assert post.archived_at is not None
        assert post.deleted_at is not None
        actions = set(session.scalars(select(AuditLog.action)).all())
        assert {
            "post.close",
            "post.reopen",
            "post.archive",
            "post.delete",
        }.issubset(actions)


def test_archived_and_deleted_posts_are_not_returned_by_public_reads(monkeypatch):
    factory = _factory()
    with factory() as session:
        session.add(
            Topic(
                id=1,
                channel="competition",
                title="公开话题",
                short_title="公开话题",
                organizer="南京大学",
                organizer_key="nju",
                canonical_event_key="public-topic",
                edition="2026",
                summary="正常话题",
                content="正常话题",
                created_by=1,
            )
        )
        session.add_all(
            [
                Post(
                    id=2,
                    title="已归档",
                    main_category="校园生活",
                    activity_name="已归档活动",
                    target_members=2,
                    author_id=1,
                    kind="topic_team",
                    topic_id=1,
                    status="archived",
                ),
                Post(
                    id=3,
                    title="已删除",
                    main_category="校园生活",
                    activity_name="已删除活动",
                    target_members=2,
                    author_id=1,
                    kind="topic_team",
                    topic_id=1,
                    status="deleted",
                ),
            ]
        )
        session.commit()

    monkeypatch.setattr(post_tools, "get_session", factory)
    monkeypatch.setattr(content_api, "get_session", factory)

    listed = json.loads(
        post_tools.list_posts.invoke(
            {
                "tab": "recommend",
                "page": 1,
                "page_size": 10,
                "category": "",
                "tags": "",
                "keyword": "",
                "sort": "latest",
                "kind": "",
                "topic_id": "",
            }
        )
    )
    assert [post["id"] for post in listed["list"]] == ["1"]
    assert json.loads(post_tools.get_post_detail.invoke({"post_id": "2"}))["success"] is False
    assert json.loads(post_tools.get_post_detail.invoke({"post_id": "3"}))["success"] is False
    assert content_api.topic_posts(1, "1")["data"] == []
