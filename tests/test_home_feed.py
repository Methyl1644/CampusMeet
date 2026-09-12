from __future__ import annotations

import datetime
import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import PendingRollbackError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.common import current_user_id
from storage.database.models import (
    Conversation,
    Message,
    Notification,
    Post,
    Tag,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    TopicTag,
    User,
)
from storage.database.shared.model import Base


UTC_NOW = datetime.datetime(2026, 9, 12, 12, 0, tzinfo=datetime.timezone.utc)


class PostgreSQLAbortLikeSession(Session):
    """Make SQLite retain PostgreSQL's transaction-aborted behavior after SQL errors."""

    def _execute_internal(self, *args, **kwargs):
        if self.info.get("statement_failed"):
            raise PendingRollbackError("transaction is aborted until rollback")
        try:
            return super()._execute_internal(*args, **kwargs)
        except SQLAlchemyError:
            self.info["statement_failed"] = True
            raise

    def rollback(self) -> None:
        self.info["statement_failed"] = False
        super().rollback()


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def abort_like_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(
        bind=engine,
        class_=PostgreSQLAbortLikeSession,
        expire_on_commit=False,
    )


@pytest.fixture
def session(factory):
    with factory() as db_session:
        yield db_session


@pytest.fixture
def user(session: Session) -> User:
    item = User(
        id=1,
        email="student@smail.nju.edu.cn",
        password_hash="hash",
        nickname="小紫",
        avatar="https://example.com/avatar.png",
        major="计算机科学与技术",
        grade="2024级",
        interests=["人工智能"],
    )
    session.add(item)
    session.flush()
    return item


def _build_home_feed(session: Session, user: User, *, now: datetime.datetime = UTC_NOW):
    home = importlib.import_module("services.home")
    return home.build_home_feed(session, user, now=now)


def _tag(session: Session, tag_id: str, name: str) -> None:
    if session.get(Tag, tag_id) is None:
        session.add(
            Tag(
                id=tag_id,
                canonical_name=name,
                category="activity",
                display_color="purple",
            )
        )
        session.flush()


def _topic(
    session: Session,
    *,
    topic_id: int,
    title: str,
    deadline: datetime.datetime | None = None,
    activity_start: datetime.datetime | None = None,
    updated_at: datetime.datetime | None = None,
    status: str = "active",
    tags: tuple[tuple[str, str], ...] = (),
) -> Topic:
    item = Topic(
        id=topic_id,
        channel="official",
        title=title,
        short_title=title,
        organizer="CampusMate",
        organizer_key="campusmate",
        canonical_event_key=f"event-{topic_id}",
        edition="2026",
        summary=f"{title}简介",
        content=f"{title}详情",
        registration_deadline=deadline,
        activity_start_at=activity_start,
        activity_end_at=(activity_start + datetime.timedelta(hours=2)) if activity_start else None,
        created_by=1,
        status=status,
        updated_at=updated_at or UTC_NOW,
    )
    session.add(item)
    session.flush()
    for tag_id, name in tags:
        _tag(session, tag_id, name)
        session.add(TopicTag(topic_id=item.id, tag_id=tag_id))
    session.flush()
    return item


def test_home_feed_prioritizes_interest_matches_and_normalizes_topic_dates(session, user):
    matched = _topic(
        session,
        topic_id=1,
        title="AI 校赛",
        deadline=(UTC_NOW + datetime.timedelta(days=3)).replace(tzinfo=None),
        tags=(("activity_ai", "人工智能"),),
    )
    _topic(
        session,
        topic_id=2,
        title="普通讲座",
        deadline=UTC_NOW + datetime.timedelta(days=2),
        tags=(("activity_lecture", "讲座"),),
    )
    _topic(session, topic_id=3, title="已下线活动", status="archived")

    feed = _build_home_feed(session, user)

    assert feed["profile"] == {
        "id": "1",
        "nickname": "小紫",
        "avatar": "https://example.com/avatar.png",
        "major": "计算机科学与技术",
        "grade": "2024级",
    }
    assert [topic["id"] for topic in feed["recommended_topics"]] == ["1", "2"]
    assert feed["recommended_topics"][0]["id"] == str(matched.id)
    assert feed["recommended_topics"][0]["recommendation_reason"] == "与你的人工智能兴趣相关"
    assert feed["recommended_topics"][0]["registration_deadline"] == "2026-09-15T12:00:00+00:00"
    assert feed["warnings"] == []


def test_recommendations_apply_all_tie_breakers_and_limit_to_eight(session, user):
    user.interests = []
    dated = _topic(session, topic_id=1, title="近期待办", deadline=UTC_NOW + datetime.timedelta(days=1))
    later = _topic(session, topic_id=2, title="稍后待办", activity_start=UTC_NOW + datetime.timedelta(days=2))
    newest_undated = _topic(
        session,
        topic_id=20,
        title="最新无日期",
        updated_at=UTC_NOW + datetime.timedelta(hours=2),
    )
    same_update_lower_id = _topic(
        session,
        topic_id=19,
        title="相同更新时间低 ID",
        updated_at=UTC_NOW + datetime.timedelta(hours=2),
    )
    older_undated = _topic(
        session,
        topic_id=18,
        title="较早无日期",
        updated_at=UTC_NOW + datetime.timedelta(hours=1),
    )
    for topic_id in range(3, 12):
        _topic(
            session,
            topic_id=topic_id,
            title=f"无日期 {topic_id}",
            updated_at=UTC_NOW - datetime.timedelta(days=topic_id),
        )

    feed = _build_home_feed(session, user)

    ids = [topic["id"] for topic in feed["recommended_topics"]]
    assert len(ids) == 8
    assert ids[:5] == [
        str(dated.id),
        str(later.id),
        str(newest_undated.id),
        str(same_update_lower_id.id),
        str(older_undated.id),
    ]


def test_followed_topics_and_deadline_reminder_use_recent_active_follows(session, user):
    nearest = _topic(session, topic_id=1, title="三天后截止", deadline=UTC_NOW + datetime.timedelta(days=3))
    _topic(session, topic_id=2, title="十五天后截止", deadline=UTC_NOW + datetime.timedelta(days=15))
    inactive = _topic(session, topic_id=3, title="已停用", deadline=UTC_NOW + datetime.timedelta(days=1), status="archived")
    for index, topic in enumerate((nearest, inactive, session.get(Topic, 2))):
        session.add(
            TopicFollow(
                topic_id=topic.id,
                user_id=user.id,
                created_at=UTC_NOW - datetime.timedelta(hours=index),
            )
        )
    session.flush()

    feed = _build_home_feed(session, user)

    assert [topic["id"] for topic in feed["followed_topics"]] == ["1", "2"]
    assert feed["followed_topics"][0]["followed"] is True
    assert feed["followed_topics"][0]["activity_start_at"] is None
    assert feed["deadline_reminder"]["id"] == "1"
    assert feed["deadline_reminder"]["days_remaining"] == 3


def test_joined_groups_timeline_and_unread_counts_use_only_memberships(session, user):
    other = User(id=2, email="other@nju.edu.cn", password_hash="hash", nickname="队友")
    session.add(other)
    session.flush()
    post = Post(
        id=1,
        title="AI 小组",
        main_category="学习与科研",
        activity_name="AI 小组",
        current_members=2,
        target_members=4,
        author_id=other.id,
    )
    session.add(post)
    session.flush()
    team = Team(
        id=1,
        post_id=post.id,
        owner_id=other.id,
        activity_name="AI 小组",
        task_list=[
            {"id": "late", "title": "提交材料", "deadline": "2026-09-14T09:00:00"},
            {
                "id": "fallback",
                "title": "讨论方案",
                "due_at": "不是日期",
                "deadline": "2026-09-15T09:00:00+00:00",
                "done": True,
            },
            {"id": "bad", "title": "整理记录", "due_at": "仍然不是日期"},
            {"id": "early", "title": "确定选题", "due_at": "2026-09-13T08:00:00+00:00", "done": False},
        ],
    )
    session.add(team)
    session.flush()
    session.add(
        TeamMember(
            team_id=team.id,
            user_id=user.id,
            member_role="member",
            created_at=UTC_NOW.replace(tzinfo=None),
        )
    )
    conversation = Conversation(
        id=1,
        post_id=post.id,
        post_author_id=other.id,
        applicant_id=user.id,
    )
    session.add(conversation)
    session.flush()
    session.add_all(
        [
            Message(conversation_id=conversation.id, sender_id=other.id, content="未读"),
            Message(conversation_id=conversation.id, sender_id=user.id, content="自己的消息"),
            Notification(
                user_id=user.id,
                event_type="team_created",
                title="成队成功",
                body="已创建小组",
                dedupe_key="home-test",
            ),
        ]
    )
    session.flush()

    feed = _build_home_feed(session, user)

    assert feed["joined_groups"] == [
        {
            "id": "1",
            "post_id": "1",
            "activity_name": "AI 小组",
            "member_role": "member",
            "created_at": "2026-09-12T12:00:00+00:00",
            "current_members": 2,
            "target_members": 4,
        }
    ]
    assert [item["task_id"] for item in feed["group_timeline"]] == [
        "early",
        "late",
        "fallback",
        "bad",
    ]
    assert feed["group_timeline"][1]["due_at"] == "2026-09-14T09:00:00+00:00"
    assert feed["group_timeline"][2]["due_at"] == "2026-09-15T09:00:00+00:00"
    assert feed["group_timeline"][2]["done"] is True
    assert feed["group_timeline"][3]["due_at"] is None
    assert feed["unread"] == {"messages": 1, "notifications": 1}


def test_home_feed_degrades_only_the_failed_section(session, user, monkeypatch):
    home = importlib.import_module("services.home")
    original = home.HOME_SECTION_BUILDERS["group_timeline"]

    def fail_group_timeline(*_args):
        raise RuntimeError("timeline unavailable")

    monkeypatch.setitem(home.HOME_SECTION_BUILDERS, "group_timeline", fail_group_timeline)
    try:
        feed = home.build_home_feed(session, user, now=UTC_NOW)
    finally:
        home.HOME_SECTION_BUILDERS["group_timeline"] = original

    assert feed["group_timeline"] == []
    assert feed["unread"] == {"messages": 0, "notifications": 0}
    assert feed["warnings"] == ["group_timeline"]


def test_home_feed_recovers_after_a_real_statement_failure(abort_like_factory, monkeypatch):
    home = importlib.import_module("services.home")
    with abort_like_factory() as session:
        user = User(
            id=1,
            email="recovery@nju.edu.cn",
            password_hash="hash",
            nickname="恢复测试",
        )
        session.add(user)
        topic = _topic(session, topic_id=1, title="已关注活动")
        session.add(TopicFollow(topic_id=topic.id, user_id=user.id, created_at=UTC_NOW))
        session.commit()
        user = session.get(User, 1)

        def fail_with_real_statement(db_session, *_args):
            db_session.execute(text("SELECT * FROM missing_home_section_table"))

        monkeypatch.setitem(
            home.HOME_SECTION_BUILDERS,
            "recommended_topics",
            fail_with_real_statement,
        )

        feed = home.build_home_feed(session, user, now=UTC_NOW)

        assert feed["recommended_topics"] == []
        assert [topic["id"] for topic in feed["followed_topics"]] == ["1"]
        assert feed["unread"] == {"messages": 0, "notifications": 0}
        assert feed["warnings"] == ["recommended_topics"]
        assert session.scalar(text("SELECT 1")) == 1


def test_home_feed_keeps_later_sections_healthy_after_multiple_failures(
    abort_like_factory,
    monkeypatch,
):
    home = importlib.import_module("services.home")
    with abort_like_factory() as session:
        user = User(
            id=1,
            email="multiple-failures@nju.edu.cn",
            password_hash="hash",
            nickname="多段降级",
        )
        session.add(user)
        topic = _topic(session, topic_id=1, title="健康关注")
        session.add_all(
            [
                TopicFollow(topic_id=topic.id, user_id=user.id, created_at=UTC_NOW),
                Notification(
                    user_id=user.id,
                    event_type="home_test",
                    title="未读通知",
                    body="后续分区仍可查询",
                    dedupe_key="multiple-section-failure",
                ),
            ]
        )
        session.commit()
        user = session.get(User, 1)

        def fail_recommendations(db_session, *_args):
            db_session.execute(text("SELECT * FROM missing_recommendation_table"))

        def fail_joined_groups(*_args):
            raise RuntimeError("joined groups unavailable")

        monkeypatch.setitem(
            home.HOME_SECTION_BUILDERS,
            "recommended_topics",
            fail_recommendations,
        )
        monkeypatch.setitem(
            home.HOME_SECTION_BUILDERS,
            "joined_groups",
            fail_joined_groups,
        )

        feed = home.build_home_feed(session, user, now=UTC_NOW)

    assert feed["recommended_topics"] == []
    assert feed["joined_groups"] == []
    assert [topic["id"] for topic in feed["followed_topics"]] == ["1"]
    assert feed["unread"] == {"messages": 0, "notifications": 1}
    assert feed["warnings"] == ["recommended_topics", "joined_groups"]


def test_home_feed_queries_compile_for_postgresql_with_bounded_ordering():
    home = importlib.import_module("services.home")
    dialect = postgresql.dialect()

    ranked_sql = str(
        home._ranked_topics_statement(["人工智能"], UTC_NOW).compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True},
        )
    )
    followed_sql = str(
        home._followed_topics_statement(7).compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True},
        )
    )
    reminder_sql = str(
        home._deadline_reminder_statement(7, UTC_NOW).compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "LIMIT 8" in ranked_sql
    ranked_order_terms = [
        "count(topic_tags.tag_id)",
        "anon_1.next_date IS NULL",
        "anon_1.next_date ASC",
        "topics.updated_at DESC",
        "topics.id DESC",
    ]
    ranked_positions = [ranked_sql.index(term) for term in ranked_order_terms]
    assert ranked_positions == sorted(ranked_positions)
    assert "LIMIT 4" in followed_sql
    assert "topic_follows.user_id = 7" in followed_sql
    assert "ORDER BY topic_follows.created_at DESC, topics.id DESC" in followed_sql
    assert "LIMIT 1" in reminder_sql
    assert "topic_follows.user_id = 7" in reminder_sql
    assert "ORDER BY topics.registration_deadline ASC, topics.id DESC" in reminder_sql


def test_home_feed_query_plan_stays_bounded_as_the_catalog_grows(session, user):
    user.interests = ["人工智能"]
    for topic_id in range(1, 65):
        tag = (
            ("activity_ai", "人工智能")
            if topic_id % 2
            else (f"activity_{topic_id}", f"标签 {topic_id}")
        )
        topic = _topic(
            session,
            topic_id=topic_id,
            title=f"活动 {topic_id}",
            deadline=UTC_NOW + datetime.timedelta(days=(topic_id % 10) + 1),
            tags=(tag,),
        )
        if topic_id <= 6:
            session.add(
                TopicFollow(
                    topic_id=topic.id,
                    user_id=user.id,
                    created_at=UTC_NOW - datetime.timedelta(minutes=topic_id),
                )
            )
    session.flush()

    statement_count = 0
    largest_parameter_count = 0

    def count_statement(_connection, _cursor, _statement, parameters, _context, _many):
        nonlocal statement_count, largest_parameter_count
        statement_count += 1
        if isinstance(parameters, (list, tuple)):
            largest_parameter_count = max(largest_parameter_count, len(parameters))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        feed = _build_home_feed(session, user)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert len(feed["recommended_topics"]) == 8
    assert len(feed["followed_topics"]) == 4
    assert statement_count <= 18
    assert largest_parameter_count <= 20


def test_home_feed_limits_joined_groups_and_timeline_items(session, user):
    for team_id in range(1, 6):
        post = Post(
            id=team_id,
            title=f"小组 {team_id}",
            main_category="学习与科研",
            activity_name=f"小组 {team_id}",
            current_members=team_id,
            target_members=6,
            author_id=user.id,
        )
        session.add(post)
        session.flush()
        team = Team(
            id=team_id,
            post_id=post.id,
            owner_id=user.id,
            activity_name=post.activity_name,
            task_list=[
                {
                    "id": f"task-{team_id}-{task_id}",
                    "title": f"任务 {team_id}-{task_id}",
                    "due_at": (UTC_NOW + datetime.timedelta(days=team_id, minutes=task_id)).isoformat(),
                }
                for task_id in range(3)
            ],
        )
        session.add(team)
        session.flush()
        session.add(
            TeamMember(
                team_id=team.id,
                user_id=user.id,
                member_role="owner",
                created_at=UTC_NOW + datetime.timedelta(minutes=team_id),
            )
        )
    session.flush()

    feed = _build_home_feed(session, user)

    assert [group["id"] for group in feed["joined_groups"]] == ["5", "4", "3", "2"]
    assert len(feed["group_timeline"]) == 12
    assert feed["group_timeline"][0]["task_id"] == "task-1-0"
    assert feed["group_timeline"][-1]["task_id"] == "task-4-2"


def test_home_endpoint_requires_auth_wraps_contract_and_rejects_missing_users(factory, monkeypatch):
    home_api = importlib.import_module("api.home")
    app = FastAPI()
    app.include_router(home_api.router, prefix="/api")
    monkeypatch.setattr(home_api, "get_session", factory)

    with TestClient(app) as client:
        assert client.get("/api/home").status_code == 401

        app.dependency_overrides[current_user_id] = lambda: "1"
        with factory() as session:
            session.add(User(id=1, email="home@nju.edu.cn", password_hash="hash", nickname="首页用户"))
            topic = _topic(
                session,
                topic_id=1,
                title="首页活动",
                deadline=UTC_NOW + datetime.timedelta(days=3),
                tags=(("activity_ai", "人工智能"),),
            )
            session.add(TopicFollow(topic_id=topic.id, user_id=1, created_at=UTC_NOW))
            session.commit()
        response = client.get("/api/home")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"code", "message", "data"}
        assert payload["code"] == 0
        assert payload["message"] == "ok"
        assert set(payload["data"]) == {
            "profile",
            "deadline_reminder",
            "recommended_topics",
            "followed_topics",
            "joined_groups",
            "group_timeline",
            "unread",
            "warnings",
        }
        assert set(payload["data"]["profile"]) == {"id", "nickname", "avatar", "major", "grade"}
        topic_keys = {
            "id",
            "channel",
            "title",
            "short_title",
            "organizer",
            "edition",
            "summary",
            "content",
            "source_url",
            "source_status",
            "cover_url",
            "follower_count",
            "followed",
            "tags",
            "status",
            "trust_badges",
            "responsible_people",
            "registration_deadline",
            "activity_start_at",
            "activity_end_at",
        }
        recommended = payload["data"]["recommended_topics"][0]
        assert set(recommended) == topic_keys | {"recommendation_reason"}
        assert recommended["source_url"] is None
        assert recommended["cover_url"] is None
        assert set(recommended["tags"][0]) == {
            "tag_id",
            "canonical_name",
            "category",
            "display_color",
        }
        assert set(recommended["trust_badges"][0]) == {"kind", "label"}
        assert recommended["responsible_people"] == []
        assert set(payload["data"]["deadline_reminder"]) == topic_keys | {"days_remaining"}
        assert set(payload["data"]["unread"]) == {"messages", "notifications"}

        response_schema = app.openapi()["paths"]["/api/home"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/HomeFeedResponse"}
        schemas = app.openapi()["components"]["schemas"]
        assert set(schemas["HomeOfficialTrustBadge"]["properties"]) == {"kind", "label"}
        assert set(schemas["HomeVerifiedOrganizationTrustBadge"]["required"]) == {
            "kind",
            "label",
            "organization_name",
        }

        app.dependency_overrides[current_user_id] = lambda: "999"
        missing = client.get("/api/home")

    assert missing.status_code == 401
    assert missing.json() == {"detail": "登录状态已失效"}
