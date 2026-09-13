from __future__ import annotations

import datetime
import importlib
import importlib.util
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from api.common import current_user_id
from services.deadlines import parse_deadline_at
from storage.database.models import (
    Application,
    AuditLog,
    Notification,
    Post,
    PostBookmark,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    User,
)
from storage.database.shared.model import Base


NOW = datetime.datetime(2026, 9, 13, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def database(tmp_path):
    database_path = (tmp_path / "task-four.sqlite3").as_posix()
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield engine, factory
    finally:
        engine.dispose()


@pytest.fixture
def api_app(database, monkeypatch):
    engine, factory = database
    content_api = importlib.import_module("api.content")
    explore_api = importlib.import_module("api.explore")
    posts_api = importlib.import_module("api.posts")

    app = FastAPI()
    app.include_router(posts_api.router, prefix="/api")
    app.include_router(content_api.router, prefix="/api")
    app.include_router(explore_api.router, prefix="/api")
    monkeypatch.setattr(posts_api, "get_session", factory)
    monkeypatch.setattr(content_api, "get_session", factory)
    monkeypatch.setattr(explore_api, "get_session", factory)

    favorite_spec = importlib.util.find_spec("api.favorites")
    if favorite_spec is not None:
        favorites_api = importlib.import_module("api.favorites")
        app.include_router(favorites_api.router, prefix="/api")
        monkeypatch.setattr(favorites_api, "get_session", factory)

    auth = {"user_id": "2"}
    app.dependency_overrides[current_user_id] = lambda: auth["user_id"]
    return app, auth, engine, factory


def _user(user_id: int, nickname: str) -> User:
    return User(
        id=user_id,
        email=f"student-{user_id}@smail.nju.edu.cn",
        password_hash="hash",
        nickname=nickname,
        auth_status="verified",
    )


def _topic(
    session,
    topic_id: int,
    *,
    owner_id: int = 1,
    status: str = "active",
    participation_mode: str = "official_signup",
    capacity: int = 3,
) -> Topic:
    topic = Topic(
        id=topic_id,
        channel="official",
        title=f"活动 {topic_id}",
        short_title=f"活动 {topic_id}",
        organizer="CampusMate",
        organizer_key=f"organizer-{topic_id}",
        canonical_event_key=f"event-{topic_id}",
        edition="2026",
        summary="活动简介",
        content="活动详情",
        source_url=f"https://example.test/topics/{topic_id}",
        participation_mode=participation_mode,
        capacity=capacity,
        registration_deadline=NOW + datetime.timedelta(days=2),
        activity_start_at=NOW + datetime.timedelta(days=4),
        activity_end_at=NOW + datetime.timedelta(days=5),
        created_by=owner_id,
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(topic)
    session.flush()
    return topic


def _post(
    session,
    post_id: int,
    *,
    author_id: int = 1,
    topic_id: int | None = None,
    purpose: str = "team_recruitment",
    join_mode: str = "application",
    status: str = "recruiting",
    target_members: int = 3,
    current_members: int = 1,
    updated_at: datetime.datetime | None = None,
) -> Post:
    deadline = "2026-09-20T12:00:00+00:00"
    post = Post(
        id=post_id,
        title=f"组队 {post_id}",
        description="组队详情",
        source_type="user",
        kind="topic_team" if topic_id else "casual_invitation",
        purpose=purpose,
        join_mode=join_mode,
        topic_id=topic_id,
        main_category="竞赛与项目",
        tags=[],
        activity_name=f"组队 {post_id}",
        current_members=current_members,
        target_members=target_members,
        needed_roles=["算法"],
        school_scope="仙林校区",
        deadline=deadline,
        deadline_at=parse_deadline_at(deadline),
        risk_level="low",
        status=status,
        author_id=author_id,
        created_at=updated_at or NOW,
        updated_at=updated_at or NOW,
    )
    session.add(post)
    session.flush()
    return post


def _seed_users(factory) -> None:
    with factory() as session:
        session.add_all(
            [_user(1, "发起人"), _user(2, "参与者"), _user(3, "候补参与者")]
        )
        session.commit()


def _race_two_requests(app: FastAPI, method: str, path: str):
    def request_once():
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.request(method, path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(lambda _index: request_once(), range(2)))


def _synchronize_first_two_statements(engine, matcher):
    barrier = threading.Barrier(2)
    lock = threading.Lock()
    matched = 0

    def synchronize(_connection, _cursor, statement, *_args):
        nonlocal matched
        if not matcher(statement.lower()):
            return
        with lock:
            matched += 1
            current = matched
        if current <= 2:
            barrier.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", synchronize)
    return synchronize


def test_favorite_put_delete_are_idempotent_and_refresh_explore_projections(api_app):
    app, _auth, _engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1)
        _post(session, 1, topic_id=topic.id)
        session.commit()

    with TestClient(app) as client:
        first_topic = client.put("/api/favorites/topics/1")
        second_topic = client.put("/api/favorites/topics/1")
        first_post = client.put("/api/favorites/posts/1")
        second_post = client.put("/api/favorites/posts/1")

        assert first_topic.status_code == second_topic.status_code == 200
        assert first_topic.json()["data"] == second_topic.json()["data"] == {
            "topic_id": "1",
            "favorite": True,
            "followed": True,
            "follower_count": 1,
        }
        assert first_post.status_code == second_post.status_code == 200
        assert first_post.json()["data"] == second_post.json()["data"] == {
            "post_id": "1",
            "bookmark": True,
        }
        assert client.get("/api/explore/activities/1").json()["data"]["favorite"] is True
        assert client.get("/api/explore/groups/1").json()["data"]["bookmark"] is True

        first_topic_delete = client.delete("/api/favorites/topics/1")
        second_topic_delete = client.delete("/api/favorites/topics/1")
        first_post_delete = client.delete("/api/favorites/posts/1")
        second_post_delete = client.delete("/api/favorites/posts/1")

        assert first_topic_delete.json()["data"] == second_topic_delete.json()["data"] == {
            "topic_id": "1",
            "favorite": False,
            "followed": False,
            "follower_count": 0,
        }
        assert first_post_delete.json()["data"] == second_post_delete.json()["data"] == {
            "post_id": "1",
            "bookmark": False,
        }
        assert client.get("/api/explore/activities/1").json()["data"]["favorite"] is False
        assert client.get("/api/explore/groups/1").json()["data"]["bookmark"] is False

        assert client.post("/api/topics/1/follow").json()["data"]["followed"] is True
        assert client.post("/api/topics/1/follow").json()["data"]["followed"] is False

    with factory() as session:
        assert session.query(TopicFollow).count() == 0
        assert session.query(PostBookmark).count() == 0


def test_favorites_hide_unavailable_content_but_allow_public_full_and_closed_posts(
    api_app,
):
    app, _auth, _engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        _topic(session, 1, status="hidden")
        _post(session, 1, status="hidden")
        _post(session, 2, status="deleted")
        _post(session, 3, status="full", target_members=1)
        _post(session, 4, status="closed")
        session.commit()

    with TestClient(app) as client:
        for method in (client.put, client.delete):
            assert method("/api/favorites/topics/999").status_code == 404
            assert method("/api/favorites/topics/1").status_code == 404
            assert method("/api/favorites/posts/999").status_code == 404
            assert method("/api/favorites/posts/1").status_code == 404
            assert method("/api/favorites/posts/2").status_code == 404
        assert client.put("/api/favorites/posts/3").status_code == 200
        assert client.put("/api/favorites/posts/4").status_code == 200
        assert client.get("/api/explore/groups/3").json()["data"]["bookmark"] is True
        assert client.get("/api/explore/groups/4").json()["data"]["bookmark"] is True


def test_favorite_uniqueness_races_return_success_without_duplicate_rows(api_app):
    app, _auth, engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        _topic(session, 1)
        _post(session, 1)
        session.commit()

    topic_sync = _synchronize_first_two_statements(
        engine,
        lambda statement: statement.startswith("insert into topic_follows"),
    )
    try:
        topic_responses = _race_two_requests(app, "PUT", "/api/favorites/topics/1")
    finally:
        event.remove(engine, "before_cursor_execute", topic_sync)

    post_sync = _synchronize_first_two_statements(
        engine,
        lambda statement: statement.startswith("insert into post_bookmarks"),
    )
    try:
        post_responses = _race_two_requests(app, "PUT", "/api/favorites/posts/1")
    finally:
        event.remove(engine, "before_cursor_execute", post_sync)

    assert [response.status_code for response in topic_responses] == [200, 200]
    assert [response.status_code for response in post_responses] == [200, 200]
    with factory() as session:
        assert session.query(TopicFollow).count() == 1
        assert session.query(PostBookmark).count() == 1


def test_direct_join_retries_emit_one_membership_notification_and_audit(api_app):
    app, _auth, _engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1)
        _post(
            session,
            1,
            topic_id=topic.id,
            purpose="official_signup",
            join_mode="direct",
        )
        session.commit()

    with TestClient(app) as client:
        first = client.post("/api/posts/1/join")
        second = client.post("/api/posts/1/join")
        detail = client.get("/api/explore/groups/1")
        activity = client.get("/api/explore/activities/1")

    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert first.json()["data"]["join_state"] == "joined"
    assert first.json()["data"]["current_members"] == 2
    assert detail.json()["data"]["join_state"] == "joined"
    assert activity.json()["data"]["participation_state"] == "joined"
    assert activity.json()["data"]["participant_count"] == 2

    with factory() as session:
        team = session.scalar(select(Team).where(Team.post_id == 1))
        assert team is not None
        assert session.query(Team).count() == 1
        assert session.query(TeamMember).count() == 2
        notification = session.query(Notification).one()
        assert notification.user_id == 1
        assert notification.event_type == "team.member_joined"
        assert notification.target_type == "team"
        audit = (
            session.query(AuditLog)
            .filter(AuditLog.action == "post.direct_join")
            .one()
        )
        assert audit.user_id == 2
        assert audit.target_id == "1"
        assert session.get(User, 2).team_count == 1


def test_direct_join_handles_uniqueness_race_without_duplicate_effects(api_app):
    app, _auth, engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1, capacity=3)
        post = _post(
            session,
            1,
            topic_id=topic.id,
            purpose="official_signup",
            join_mode="direct",
        )
        team = Team(
            post_id=post.id,
            owner_id=1,
            activity_name=post.activity_name,
            status="active",
        )
        session.add(team)
        session.flush()
        session.add(TeamMember(team_id=team.id, user_id=1, member_role="owner"))
        session.commit()

    update_sync = _synchronize_first_two_statements(
        engine,
        lambda statement: statement.startswith("update posts set current_members"),
    )
    try:
        responses = _race_two_requests(app, "POST", "/api/posts/1/join")
    finally:
        event.remove(engine, "before_cursor_execute", update_sync)

    assert [response.status_code for response in responses] == [200, 200]
    assert all(response.json()["data"]["join_state"] == "joined" for response in responses)
    with factory() as session:
        post = session.get(Post, 1)
        assert session.query(Team).count() == 1
        assert session.query(TeamMember).count() == 2
        assert session.query(Notification).count() == 1
        assert (
            session.query(AuditLog)
            .filter(AuditLog.action == "post.direct_join")
            .count()
            == 1
        )
        assert post.current_members == 2
        assert post.status == "recruiting"
        assert session.get(User, 2).team_count == 1


def test_direct_join_same_user_race_succeeds_when_only_one_place_remains(api_app):
    app, _auth, engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1, capacity=2)
        post = _post(
            session,
            1,
            topic_id=topic.id,
            purpose="official_signup",
            join_mode="direct",
            target_members=2,
        )
        team = Team(
            post_id=post.id,
            owner_id=1,
            activity_name=post.activity_name,
            status="active",
        )
        session.add(team)
        session.flush()
        session.add(TeamMember(team_id=team.id, user_id=1, member_role="owner"))
        session.commit()

    update_sync = _synchronize_first_two_statements(
        engine,
        lambda statement: statement.startswith("update posts set current_members"),
    )
    try:
        responses = _race_two_requests(app, "POST", "/api/posts/1/join")
    finally:
        event.remove(engine, "before_cursor_execute", update_sync)

    assert [response.status_code for response in responses] == [200, 200]
    assert {response.json()["data"]["member_id"] for response in responses} == {"2"}
    assert all(response.json()["data"]["join_state"] == "joined" for response in responses)
    assert all(response.json()["data"]["current_members"] == 2 for response in responses)
    with factory() as session:
        assert session.query(Team).count() == 1
        assert session.query(TeamMember).count() == 2
        assert session.query(Notification).count() == 1
        assert (
            session.query(AuditLog)
            .filter(AuditLog.action == "post.direct_join")
            .count()
            == 1
        )
        assert session.get(Post, 1).status == "full"
        assert session.get(User, 2).team_count == 1


def test_direct_join_failure_after_writes_rolls_back_the_whole_operation(
    api_app,
    monkeypatch,
):
    app, _auth, _engine, factory = api_app
    posts_api = importlib.import_module("api.posts")
    original_join = posts_api.join_post_directly
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1, capacity=3)
        _post(
            session,
            1,
            topic_id=topic.id,
            purpose="official_signup",
            join_mode="direct",
        )
        session.commit()

    def fail_after_all_writes(session, post, user):
        original_join(session, post, user)
        session.flush()
        raise RuntimeError("forced failure after direct-join writes")

    monkeypatch.setattr(posts_api, "join_post_directly", fail_after_all_writes)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/posts/1/join")

    assert response.status_code == 500
    with factory() as session:
        assert session.query(Team).count() == 0
        assert session.query(TeamMember).count() == 0
        assert session.query(Notification).count() == 0
        assert session.query(AuditLog).count() == 0
        assert session.get(Post, 1).current_members == 1
        assert session.get(Post, 1).status == "recruiting"
        assert session.get(User, 1).team_count == 0
        assert session.get(User, 2).team_count == 0


def test_direct_join_returns_stable_errors_and_preserves_application_mode(
    api_app,
    monkeypatch,
):
    app, _auth, _engine, factory = api_app
    application_tools = importlib.import_module("tools.application_tools")
    monkeypatch.setattr(application_tools, "get_session", factory)
    _seed_users(factory)
    with factory() as session:
        closed_topic = _topic(session, 2)
        full_topic = _topic(session, 3, capacity=1)
        _post(session, 1, status="hidden", purpose="official_signup", join_mode="direct")
        _post(
            session,
            2,
            topic_id=closed_topic.id,
            status="closed",
            purpose="official_signup",
            join_mode="direct",
        )
        _post(
            session,
            3,
            topic_id=full_topic.id,
            status="full",
            purpose="official_signup",
            join_mode="direct",
            target_members=1,
        )
        _post(session, 4, purpose="team_recruitment", join_mode="application")
        session.commit()

    with TestClient(app) as client:
        assert client.post("/api/posts/999/join").status_code == 404
        assert client.post("/api/posts/1/join").status_code == 404
        closed = client.post("/api/posts/2/join")
        full = client.post("/api/posts/3/join")
        application_mode = client.post("/api/posts/4/join")

    assert closed.status_code == 409
    assert closed.json()["detail"]["code"] == "participation.closed"
    assert full.status_code == 409
    assert full.json()["detail"]["code"] == "participation.full"
    assert application_mode.status_code == 409
    assert application_mode.json()["detail"]["code"] == "participation.invalid_join_mode"

    application = application_tools.create_application.invoke(
        {
            "user_id": "2",
            "post_id": "4",
            "role_wanted": "队员",
            "experience": "有经验",
            "available_time": "周末",
            "reason": "希望参加",
            "questions": "",
        }
    )
    assert json.loads(application)["success"] is True
    with factory() as session:
        assert session.query(Application).count() == 1
        assert session.query(Team).count() == 0


def test_related_posts_are_authenticated_filtered_bounded_and_stable(api_app):
    app, _auth, _engine, factory = api_app
    _seed_users(factory)
    with factory() as session:
        topic = _topic(session, 1, participation_mode="open_team")
        _topic(session, 2, status="hidden", participation_mode="open_team")
        for post_id in range(1, 26):
            _post(
                session,
                post_id,
                topic_id=topic.id,
                purpose="discussion" if post_id % 2 == 0 else "team_recruitment",
                join_mode="none" if post_id % 2 == 0 else "application",
                status=(
                    "hidden"
                    if post_id == 24
                    else "deleted"
                    if post_id == 25
                    else "recruiting"
                ),
                updated_at=NOW + datetime.timedelta(minutes=post_id),
            )
        session.commit()

    with TestClient(app) as client:
        page_one = client.get(
            "/api/topics/1/related-posts",
            params={"purpose": "discussion", "page": 1, "page_size": 5},
        )
        page_two = client.get(
            "/api/topics/1/related-posts",
            params={"purpose": "discussion", "page": 2, "page_size": 5},
        )
        assert client.get("/api/topics/1/related-posts?page_size=21").status_code == 422
        assert client.get("/api/topics/1/related-posts?purpose=unknown").status_code == 422
        assert client.get("/api/topics/2/related-posts").status_code == 404
        assert client.get("/api/topics/999/related-posts").status_code == 404

    assert page_one.status_code == page_two.status_code == 200
    assert page_one.json()["data"]["total"] == 11
    assert page_one.json()["data"]["page_size"] == 5
    assert [item["id"] for item in page_one.json()["data"]["list"]] == [
        "22",
        "20",
        "18",
        "16",
        "14",
    ]
    assert [item["id"] for item in page_two.json()["data"]["list"]] == [
        "12",
        "10",
        "8",
        "6",
        "4",
    ]
    assert all(item["purpose"] == "discussion" for item in page_one.json()["data"]["list"])

    unauthenticated = FastAPI()
    content_api = importlib.import_module("api.content")
    unauthenticated.include_router(content_api.router, prefix="/api")
    with TestClient(unauthenticated) as client:
        assert client.get("/api/topics/1/related-posts").status_code == 401


def test_main_registers_task_four_routes():
    main = importlib.import_module("main")
    paths = main.app.openapi()["paths"]

    assert "put" in paths["/api/favorites/topics/{topic_id}"]
    assert "delete" in paths["/api/favorites/topics/{topic_id}"]
    assert "put" in paths["/api/favorites/posts/{post_id}"]
    assert "delete" in paths["/api/favorites/posts/{post_id}"]
    assert "post" in paths["/api/posts/{post_id}/join"]
    assert "get" in paths["/api/topics/{topic_id}/related-posts"]
