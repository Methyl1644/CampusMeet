from __future__ import annotations

import datetime
import importlib
import importlib.util

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.common import current_user_id
from api import auth as auth_api
from services.deadlines import parse_deadline_at
from storage.database.models import (
    Application,
    Post,
    PostBookmark,
    Team,
    TeamMember,
    Topic,
    TopicFollow,
    User,
)
from storage.database.shared.model import Base


NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


@pytest.fixture
def personal_api():
    if importlib.util.find_spec("api.personal") is None:
        return None
    return importlib.import_module("api.personal")


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add_all(
            [
                User(
                    id=1,
                    email="member@smail.nju.edu.cn",
                    password_hash="hash",
                    nickname="成员",
                    major=" 软件工程 ",
                    grade=" 大二 ",
                    bio="一起做有意思的事",
                    interests=["人工智能", "数学建模", "羽毛球"],
                    looking_for=["寻找长期伙伴"],
                    skills=["Python"],
                    availability={"weekday_evening": True},
                    profile_visibility={
                        "major": False,
                        "grade": True,
                        "interests": False,
                        "skills": True,
                        "availability": False,
                        "contact": False,
                        "activities": True,
                        "groups": False,
                    },
                    wechat="private_wechat",
                    auth_status="verified",
                ),
                User(id=2, email="visitor@smail.nju.edu.cn", password_hash="hash", nickname="访客"),
                User(id=3, email="owner@smail.nju.edu.cn", password_hash="hash", nickname="发起人"),
            ]
        )
        session.flush()

        def topic(topic_id: int, offset: int, *, status: str = "active") -> Topic:
            value = Topic(
                id=topic_id,
                channel="official",
                title=f"活动 {topic_id}",
                short_title=f"活动 {topic_id}",
                organizer="CampusMate",
                organizer_key=f"org-{topic_id}",
                canonical_event_key=f"event-{topic_id}",
                edition="2026",
                summary="活动简介",
                content="活动详情",
                created_by=3,
                status=status,
                registration_deadline=NOW + datetime.timedelta(days=offset - 1),
                activity_start_at=NOW + datetime.timedelta(days=offset),
                activity_end_at=NOW + datetime.timedelta(days=offset + 1),
                created_at=NOW,
                updated_at=NOW,
            )
            session.add(value)
            session.flush()
            return value

        def post(post_id: int, *, topic_id: int | None = None, status: str = "recruiting") -> Post:
            deadline = (NOW + datetime.timedelta(days=10)).isoformat()
            value = Post(
                id=post_id,
                title=f"组队 {post_id}",
                description="组队详情",
                main_category="竞赛与项目",
                activity_name=f"组队 {post_id}",
                target_members=4,
                current_members=1,
                needed_roles=["算法"],
                deadline=deadline,
                deadline_at=parse_deadline_at(deadline),
                author_id=3,
                topic_id=topic_id,
                status=status,
                created_at=NOW + datetime.timedelta(minutes=post_id),
                updated_at=NOW + datetime.timedelta(minutes=post_id),
            )
            session.add(value)
            session.flush()
            return value

        upcoming = topic(1, 5)
        saved = topic(2, 8)
        past_end = topic(3, -5)
        hidden = topic(4, 9, status="hidden")
        undated = topic(5, 9)
        undated.registration_deadline = None
        undated.activity_start_at = None
        undated.activity_end_at = None
        linked_one = post(1, topic_id=upcoming.id)
        linked_two = post(2, topic_id=upcoming.id)
        past_post = post(3, topic_id=past_end.id, status="closed")
        pending_post = post(4)
        saved_post = post(5)
        archived_post = post(6, status="closed")
        hidden_post = post(7, status="hidden")
        undated_post = post(8, topic_id=undated.id)
        teams = [
            Team(id=1, post_id=linked_one.id, owner_id=3, activity_name="A"),
            Team(id=2, post_id=linked_two.id, owner_id=3, activity_name="B"),
            Team(id=3, post_id=past_post.id, owner_id=3, activity_name="C", status="archived"),
            Team(id=4, post_id=archived_post.id, owner_id=3, activity_name="D", status="archived"),
            Team(id=5, post_id=undated_post.id, owner_id=3, activity_name="E", status="archived"),
        ]
        session.add_all(teams)
        session.flush()
        session.add_all(
            [TeamMember(team_id=team.id, user_id=1, created_at=NOW) for team in teams]
        )
        session.add_all(
            [
                TopicFollow(topic_id=saved.id, user_id=1, created_at=NOW),
                TopicFollow(topic_id=hidden.id, user_id=1, created_at=NOW),
                PostBookmark(post_id=saved_post.id, user_id=1, created_at=NOW),
                PostBookmark(post_id=hidden_post.id, user_id=1, created_at=NOW),
                Application(
                    post_id=pending_post.id,
                    applicant_id=1,
                    role_wanted="队员",
                    experience="有经验",
                    available_time="周末",
                    reason="想参加",
                    status="pending",
                    created_at=NOW,
                ),
            ]
        )
        session.commit()
    return session_factory


@pytest.fixture
def client(factory, personal_api, monkeypatch):
    app = FastAPI()
    if personal_api is not None:
        app.include_router(personal_api.router, prefix="/api")
        monkeypatch.setattr(personal_api, "get_session", factory)
    auth = {"user_id": "1"}
    app.dependency_overrides[current_user_id] = lambda: auth["user_id"]
    with TestClient(app) as test_client:
        yield test_client, auth


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/me/activities?view=attending", ["1"]),
        ("/api/me/activities?view=saved", ["2"]),
        ("/api/me/activities?view=past", ["3"]),
        ("/api/me/groups?view=joined", ["2", "1"]),
        ("/api/me/groups?view=pending", ["4"]),
        ("/api/me/groups?view=saved", ["5"]),
        ("/api/me/groups?view=archived", ["8", "6", "3"]),
    ],
)
def test_personal_collection_views_are_deduplicated_public_and_deterministic(client, path, expected):
    test_client, _auth = client

    response = test_client.get(path)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]["list"]] == expected


def test_personal_collection_pagination_is_bounded(client):
    test_client, _auth = client

    assert test_client.get("/api/me/activities?page=0").status_code == 422
    assert test_client.get("/api/me/groups?page_size=41").status_code == 422


def test_post_author_sees_owned_groups_even_before_legacy_membership_backfill(client):
    test_client, auth = client
    auth["user_id"] = "3"

    response = test_client.get("/api/me/groups?view=joined")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["data"]["list"]} >= {"4", "5"}


def test_public_profile_omits_hidden_fields_but_owner_sees_them(client):
    test_client, auth = client
    auth["user_id"] = "2"

    visitor = test_client.get("/api/profiles/1")

    assert visitor.status_code == 200
    data = visitor.json()["data"]
    assert data["nickname"] == "成员"
    assert data["grade"] == " 大二 "
    assert data["skills"] == ["Python"]
    assert [item["id"] for item in data["activities"]] == ["1"]
    participant = data["activities"][0]["participant_preview"][0]
    assert "major" not in participant
    assert participant["grade"] == " 大二 "
    for hidden in ("major", "interests", "availability", "contact", "groups"):
        assert hidden not in data

    auth["user_id"] = "1"
    owner = test_client.get("/api/profiles/1").json()["data"]
    assert owner["major"] == " 软件工程 "
    assert owner["contact"] == {"wechat": "private_wechat"}
    assert [item["id"] for item in owner["groups"]] == ["2", "1"]


def test_public_profile_missing_user_is_404(client):
    test_client, _auth = client

    response = test_client.get("/api/profiles/999")

    assert response.status_code == 404


def test_owner_profile_patch_reuses_onboarding_normalization_and_rejects_invalid_input(client, factory):
    test_client, _auth = client

    response = test_client.patch(
        "/api/me/profile",
        json={
            "nickname": "  新名称  ",
            "interests": [" 人工智能 ", "数学建模", "人工智能"],
            "skills": [" Python ", "Python", " SQL "],
            "profile_visibility": {"major": True, "groups": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["nickname"] == "新名称"
    assert response.json()["data"]["interests"] == ["人工智能", "数学建模"]
    assert response.json()["data"]["skills"] == ["Python", "SQL"]
    with factory() as session:
        user = session.get(User, 1)
        assert user.nickname == "新名称"
        assert user.profile_visibility["major"] is True
        assert user.profile_visibility["groups"] is True

    assert test_client.patch("/api/me/profile", json={"interests": ["自造兴趣"]}).status_code == 422
    assert test_client.patch("/api/me/profile", json={"site_role": "operator"}).status_code == 422


def test_legacy_auth_profile_patch_preserves_its_user_response_contract(factory, monkeypatch):
    app = FastAPI()
    app.include_router(auth_api.router, prefix="/api")
    app.dependency_overrides[current_user_id] = lambda: "1"
    monkeypatch.setattr(auth_api, "get_session", factory)

    with TestClient(app) as test_client:
        response = test_client.patch(
            "/api/auth/profile",
            json={"nickname": "兼容更新", "skills": ["Python"]},
        )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "1"
    assert response.json()["data"]["email"] == "member@smail.nju.edu.cn"
    assert response.json()["data"]["nickname"] == "兼容更新"
