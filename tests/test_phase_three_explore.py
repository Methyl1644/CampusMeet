from __future__ import annotations

import datetime
import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.common import current_user_id
from storage.database.models import (
    Application,
    Post,
    PostBookmark,
    PostTag,
    Tag,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    TopicTag,
    User,
)
from storage.database.shared.model import Base


NOW = datetime.datetime(2026, 9, 13, 12, 0, tzinfo=datetime.timezone.utc)


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
def session(factory):
    with factory() as db_session:
        yield db_session


@pytest.fixture
def viewer(session: Session) -> User:
    user = _user(1, "浏览者")
    session.add(user)
    session.flush()
    return user


def _explore():
    return importlib.import_module("services.explore")


def _user(user_id: int, nickname: str) -> User:
    return User(
        id=user_id,
        email=f"student-{user_id}@smail.nju.edu.cn",
        password_hash="hash",
        nickname=nickname,
        avatar=f"https://example.test/avatars/{user_id}.png",
        major="软件工程",
        grade="2024级",
        auth_status="verified",
    )


def _tag(session: Session, tag_id: str, name: str, *, category: str = "activity") -> Tag:
    tag = session.get(Tag, tag_id)
    if tag is None:
        tag = Tag(
            id=tag_id,
            canonical_name=name,
            category=category,
            display_color="purple",
            sort_order=1,
        )
        session.add(tag)
        session.flush()
    return tag


def _topic(
    session: Session,
    topic_id: int,
    *,
    title: str,
    channel: str = "official",
    campus: str | None = "仙林校区",
    participation_mode: str = "open_team",
    status: str = "active",
    cover_url: str | None = None,
    updated_at: datetime.datetime = NOW,
) -> Topic:
    topic = Topic(
        id=topic_id,
        channel=channel,
        title=title,
        short_title=title,
        organizer="CampusMate",
        organizer_key=f"organizer-{topic_id}",
        canonical_event_key=f"event-{topic_id}",
        edition="2026",
        summary=f"{title}简介",
        content=f"{title}完整详情",
        source_url=f"https://example.test/topics/{topic_id}",
        cover_url=cover_url,
        location_name="大学生活动中心",
        campus_scope=campus,
        capacity=30,
        participation_mode=participation_mode,
        registration_deadline=NOW + datetime.timedelta(days=2),
        activity_start_at=NOW + datetime.timedelta(days=4),
        activity_end_at=NOW + datetime.timedelta(days=5),
        created_by=1,
        status=status,
        created_at=updated_at,
        updated_at=updated_at,
    )
    session.add(topic)
    session.flush()
    return topic


def _post(
    session: Session,
    post_id: int,
    *,
    author_id: int,
    title: str,
    topic_id: int | None = None,
    category: str = "竞赛与项目",
    purpose: str = "team_recruitment",
    join_mode: str = "application",
    status: str = "recruiting",
    campus: str = "仙林校区",
    deadline: str = "2026-09-20T12:00:00+00:00",
    cover_url: str | None = None,
    updated_at: datetime.datetime = NOW,
) -> Post:
    post = Post(
        id=post_id,
        title=title,
        description=f"{title}详情",
        cover_url=cover_url,
        source_type="user",
        kind="topic_team" if topic_id else "casual_invitation",
        purpose=purpose,
        join_mode=join_mode,
        topic_id=topic_id,
        main_category=category,
        tags=[],
        activity_name=title,
        current_members=1,
        target_members=12,
        needed_roles=["算法", "写作"],
        weekly_hours="每周 4 小时",
        school_scope=campus,
        deadline=deadline,
        risk_level="low",
        status=status,
        author_id=author_id,
        created_at=updated_at,
        updated_at=updated_at,
    )
    session.add(post)
    session.flush()
    return post


def _team_with_members(
    session: Session,
    post: Post,
    member_ids: list[int],
    *,
    team_id: int | None = None,
) -> Team:
    team = Team(
        id=team_id or post.id,
        post_id=post.id,
        owner_id=post.author_id,
        activity_name=post.activity_name,
        status="active",
    )
    session.add(team)
    session.flush()
    for index, member_id in enumerate(member_ids):
        session.add(
            TeamMember(
                team_id=team.id,
                user_id=member_id,
                member_role="owner" if index == 0 else "member",
                created_at=NOW + datetime.timedelta(minutes=index),
            )
        )
    post.current_members = len(set(member_ids))
    session.flush()
    return team


def test_activity_list_combines_filters_and_uses_stable_pagination(session, viewer):
    explore = _explore()
    ai = _tag(session, "activity_ai", "人工智能")
    for topic_id in range(2, 7):
        topic = _topic(
            session,
            topic_id,
            title=f"AI 挑战赛 {topic_id}",
            channel="organization",
            participation_mode="open_team",
        )
        session.add(TopicTag(topic_id=topic.id, tag_id=ai.id))
    _topic(session, 7, title="AI 鼓楼讲座", campus="鼓楼校区")
    _topic(session, 8, title="AI 信息活动", participation_mode="information_only")
    session.flush()

    page_one = explore.list_activities(
        session,
        viewer.id,
        q="AI",
        tag_ids=[ai.id],
        date_filter="upcoming",
        status="active",
        type_filter="organization",
        campus="仙林校区",
        page=1,
        page_size=2,
        now=NOW,
    )
    page_two = explore.list_activities(
        session,
        viewer.id,
        q="AI",
        tag_ids=[ai.id],
        date_filter="upcoming",
        status="active",
        type_filter="organization",
        campus="仙林校区",
        page=2,
        page_size=2,
        now=NOW,
    )

    assert page_one["total"] == 5
    assert [item["id"] for item in page_one["list"]] == ["6", "5"]
    assert [item["id"] for item in page_two["list"]] == ["4", "3"]
    assert page_one["pages"] == 3
    assert page_one["list"][0]["tags"] == [
        {
            "tag_id": "activity_ai",
            "canonical_name": "人工智能",
            "category": "activity",
            "display_color": "purple",
        }
    ]


def test_activity_detail_deduplicates_participants_and_bounds_previews(session, viewer):
    explore = _explore()
    topic = _topic(session, 1, title="校园创新赛")
    users = [_user(user_id, f"成员 {user_id}") for user_id in range(2, 13)]
    session.add_all(users)
    session.flush()
    posts = [
        _post(session, post_id, author_id=2, title=f"关联组队 {post_id}", topic_id=topic.id)
        for post_id in range(1, 11)
    ]
    _team_with_members(session, posts[0], list(range(2, 12)), team_id=101)
    _team_with_members(session, posts[1], [2, 12], team_id=102)
    session.add(TopicFollow(topic_id=topic.id, user_id=viewer.id, created_at=NOW))
    session.add(TeamMember(team_id=101, user_id=viewer.id, member_role="member"))
    session.flush()

    detail = explore.get_activity_detail(session, topic.id, viewer.id, now=NOW)

    assert detail is not None
    assert detail["cover_url"] is None
    assert detail["cover_placeholder_key"] == "activity:official"
    assert detail["favorite"] is True
    assert detail["participation_state"] == "joined"
    assert detail["participant_count"] == 12
    assert len(detail["participant_preview"]) == 8
    assert len({item["id"] for item in detail["participant_preview"]}) == 8
    assert len(detail["related_groups"]) == 8


def test_group_list_combines_filters_and_projects_user_state(session, viewer):
    explore = _explore()
    role_tag = _tag(session, "skill_algorithm", "算法", category="skill")
    author = _user(2, "发起人")
    session.add(author)
    session.flush()
    for post_id in range(1, 5):
        post = _post(
            session,
            post_id,
            author_id=author.id,
            title=f"AI 算法组队 {post_id}",
            purpose="team_recruitment",
        )
        session.add(PostTag(post_id=post.id, tag_id=role_tag.id))
    session.add(PostBookmark(post_id=4, user_id=viewer.id, created_at=NOW))
    session.add(
        Application(
            post_id=4,
            applicant_id=viewer.id,
            role_wanted="算法",
            experience="有项目经验",
            available_time="周末",
            reason="希望参加",
            status="pending",
        )
    )
    _post(session, 5, author_id=author.id, title="鼓楼 AI 组队", campus="鼓楼校区")
    _post(session, 6, author_id=author.id, title="仙林讨论", purpose="discussion", join_mode="none")
    session.flush()

    result = explore.list_groups(
        session,
        viewer.id,
        q="AI",
        tag_ids=[role_tag.id],
        date_filter="upcoming",
        status="recruiting",
        type_filter="team_recruitment",
        campus="仙林校区",
        page=1,
        page_size=3,
        now=NOW,
    )

    assert result["total"] == 4
    assert [item["id"] for item in result["list"]] == ["4", "3", "2"]
    bookmarked = result["list"][0]
    assert bookmarked["bookmark"] is True
    assert bookmarked["join_state"] == "pending"
    assert bookmarked["cover_url"] is None
    assert bookmarked["cover_placeholder_key"] == "category:competition-project"
    assert bookmarked["author"]["nickname"] == "发起人"
    assert bookmarked["tags"][0]["canonical_name"] == "算法"


def test_group_detail_bounds_members_and_includes_linked_activity(session, viewer):
    explore = _explore()
    topic = _topic(session, 1, title="数学建模竞赛", participation_mode="official_signup")
    members = [_user(user_id, f"队员 {user_id}") for user_id in range(2, 13)]
    session.add_all(members)
    session.flush()
    post = _post(
        session,
        1,
        author_id=2,
        title="数学建模官方报名",
        topic_id=topic.id,
        purpose="official_signup",
        join_mode="direct",
    )
    _team_with_members(session, post, list(range(2, 13)), team_id=1)
    session.flush()

    detail = explore.get_group_detail(session, post.id, viewer.id, now=NOW)

    assert detail is not None
    assert len(detail["member_preview"]) == 8
    assert detail["linked_activity"] == {
        "id": "1",
        "title": "数学建模竞赛",
        "short_title": "数学建模竞赛",
        "organizer": "CampusMate",
        "cover_url": None,
        "cover_placeholder_key": "activity:official",
        "registration_deadline": "2026-09-15T12:00:00+00:00",
        "activity_start_at": "2026-09-17T12:00:00+00:00",
        "participation_mode": "official_signup",
        "status": "active",
    }
    assert detail["purpose"] == "official_signup"
    assert detail["join_mode"] == "direct"


def test_group_projection_closes_without_leaking_a_hidden_linked_activity(session, viewer):
    explore = _explore()
    author = _user(2, "发起人")
    session.add(author)
    session.flush()
    topic = _topic(session, 1, title="已隐藏活动", status="hidden")
    post = _post(session, 1, author_id=author.id, title="仍公开的组队", topic_id=topic.id)
    session.flush()

    detail = explore.get_group_detail(session, post.id, viewer.id, now=NOW)

    assert detail is not None
    assert detail["join_state"] == "closed"
    assert detail["linked_activity"] is None


def test_explore_query_counts_do_not_grow_with_page_contents(session, viewer):
    explore = _explore()
    author = _user(2, "发起人")
    session.add(author)
    session.flush()
    for item_id in range(1, 46):
        topic = _topic(session, item_id, title=f"活动 {item_id}")
        _post(session, item_id, author_id=author.id, title=f"组队 {item_id}", topic_id=topic.id)
    session.flush()

    statements = 0

    def count_statement(*_args):
        nonlocal statements
        statements += 1

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        activity_page = explore.list_activities(session, viewer.id, page_size=40, now=NOW)
        activity_statements = statements
        statements = 0
        group_page = explore.list_groups(session, viewer.id, page_size=40, now=NOW)
        group_statements = statements
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert len(activity_page["list"]) == 40
    assert len(group_page["list"]) == 40
    assert activity_statements <= 12
    assert group_statements <= 10


def test_explore_api_requires_auth_caps_pages_and_returns_404s(factory, monkeypatch):
    explore_api = importlib.import_module("api.explore")
    app = FastAPI()
    app.include_router(explore_api.router, prefix="/api")
    monkeypatch.setattr(explore_api, "get_session", factory)

    with TestClient(app) as client:
        assert client.get("/api/explore/activities").status_code == 401
        assert client.get("/api/explore/groups").status_code == 401
        app.dependency_overrides[current_user_id] = lambda: "1"
        with factory() as db_session:
            db_session.add(_user(1, "浏览者"))
            db_session.commit()

        assert client.get("/api/explore/activities?page_size=41").status_code == 422
        assert client.get("/api/explore/groups?page_size=41").status_code == 422
        assert client.get("/api/explore/activities/999").status_code == 404
        assert client.get("/api/explore/groups/999").status_code == 404

        response = client.get("/api/explore/activities?page=1&page_size=20")
        assert response.status_code == 200
        assert response.json() == {
            "code": 0,
            "message": "ok",
            "data": {"list": [], "total": 0, "page": 1, "page_size": 20, "pages": 0},
        }

    schemas = app.openapi()["components"]["schemas"]
    assert "ExploreActivityDetailResponse" in schemas
    assert "ExploreGroupDetailResponse" in schemas


def test_main_registers_all_four_explore_routes():
    main = importlib.import_module("main")
    paths = set(main.app.openapi()["paths"])

    assert {
        "/api/explore/activities",
        "/api/explore/activities/{topic_id}",
        "/api/explore/groups",
        "/api/explore/groups/{post_id}",
    } <= paths


def test_legacy_projections_gain_only_task_three_fields(session, viewer):
    from services.content import topic_to_dict
    from tools.post_tools import _post_to_dict

    topic = _topic(session, 1, title="旧活动")
    post = _post(session, 1, author_id=viewer.id, title="旧组队")
    session.flush()

    topic_payload = topic_to_dict(session, topic, viewer.id)
    post_payload = _post_to_dict(post, viewer, session)

    assert {
        "location_name",
        "campus_scope",
        "capacity",
        "participation_mode",
        "participant_count",
        "participant_preview",
        "cover_placeholder_key",
        "participation_state",
    } <= set(topic_payload)
    assert {
        "cover_url",
        "cover_placeholder_key",
        "purpose",
        "join_mode",
        "bookmark",
        "join_state",
        "member_preview",
        "linked_activity",
    } <= set(post_payload)


def test_legacy_single_post_projection_uses_the_authenticated_viewer(session, viewer):
    from tools.post_tools import _post_to_dict

    author = _user(2, "发起人")
    session.add(author)
    session.flush()
    post = _post(session, 1, author_id=author.id, title="协作编辑组队")
    session.add(PostBookmark(post_id=post.id, user_id=viewer.id, created_at=NOW))
    session.flush()

    projection = _post_to_dict(post, author, session, viewer_id=viewer.id)

    assert projection["bookmark"] is True
    assert projection["join_state"] == "available"
