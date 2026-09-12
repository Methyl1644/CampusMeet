from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import auth as auth_api
from api.common import current_user_id
from services.onboarding import (
    complete_onboarding,
    onboarding_to_dict,
    update_onboarding,
)
from storage.database.models import User
from storage.database.shared.model import Base
from tools.auth_tools import _user_to_dict
from utils.auth import hash_password


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
        session.add(
            User(
                id=1,
                email="student@smail.nju.edu.cn",
                password_hash=hash_password("Password2026"),
                nickname="student",
            )
        )
        session.commit()
    return session_factory


@pytest.fixture
def client(factory, monkeypatch):
    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[current_user_id] = lambda: "1"
    monkeypatch.setattr(auth_api, "get_session", factory)
    with TestClient(app) as test_client:
        yield test_client


def test_user_model_exposes_onboarding_defaults():
    user = User(email="new@smail.nju.edu.cn", password_hash="hash", nickname="new")

    assert {
        "onboarding_step",
        "onboarding_completed_at",
        "bio",
        "interests",
        "looking_for",
        "availability",
        "profile_visibility",
    } <= set(User.__table__.columns.keys())
    assert user.onboarding_step is None or user.onboarding_step == 1
    assert user.onboarding_completed_at is None


def test_user_model_persists_onboarding_collection_defaults(factory):
    with factory() as session:
        user = session.get(User, 1)

        assert user.onboarding_step == 1
        assert user.interests == []
        assert user.looking_for == []
        assert user.availability == {}
        assert user.profile_visibility == {}


def test_onboarding_draft_persists_each_step(factory):
    with factory() as session:
        user = session.get(User, 1)
        data = update_onboarding(
            session,
            user,
            {
                "step": 3,
                "nickname": "  小紫  ",
                "major": " 软件工程 ",
                "grade": " 大二 ",
                "interests": [" 人工智能 ", "产品设计", "人工智能", "羽毛球"],
            },
        )
        session.commit()

    with factory() as session:
        user = session.get(User, 1)
        assert data["onboarding_step"] == 3
        assert user.nickname == "小紫"
        assert user.major == "软件工程"
        assert user.grade == "大二"
        assert user.interests == ["人工智能", "产品设计", "羽毛球"]


def test_onboarding_step_is_clamped_and_never_decreases(factory):
    with factory() as session:
        user = session.get(User, 1)

        assert update_onboarding(session, user, {"step": 4})["onboarding_step"] == 4
        assert update_onboarding(session, user, {"step": -10})["onboarding_step"] == 4
        assert update_onboarding(session, user, {"step": 99})["onboarding_step"] == 6


@pytest.mark.parametrize("step", [3.0, 3.9, True, False])
def test_onboarding_step_rejects_float_and_bool_values(factory, step):
    with factory() as session:
        user = session.get(User, 1)

        with pytest.raises(ValueError, match="step 必须是整数"):
            update_onboarding(session, user, {"step": step})

        assert user.onboarding_step == 1


def test_onboarding_update_rejects_unknown_fields_before_mutating(factory):
    with factory() as session:
        user = session.get(User, 1)

        with pytest.raises(ValueError, match="未知字段"):
            update_onboarding(
                session,
                user,
                {"step": 3, "nickname": "changed", "site_role": "operator"},
            )

        assert user.onboarding_step == 1
        assert user.nickname == "student"
        assert user.site_role == "student"


def test_onboarding_update_rejects_oversized_lists_before_mutating(factory):
    with factory() as session:
        user = session.get(User, 1)

        with pytest.raises(ValueError, match="最多包含 30 项"):
            update_onboarding(
                session,
                user,
                {"step": 2, "interests": [f"兴趣{i}" for i in range(31)]},
            )

        assert user.onboarding_step == 1
        assert user.interests == []


@pytest.mark.parametrize("field", ["nickname", "major", "grade"])
def test_onboarding_completion_requires_non_empty_profile_fields(factory, field):
    values = {"nickname": "小紫", "major": "软件工程", "grade": "大二"}
    values[field] = "   "
    with factory() as session:
        user = session.get(User, 1)
        update_onboarding(
            session,
            user,
            {
                "step": 5,
                **values,
                "interests": ["人工智能", "产品设计", "羽毛球"],
            },
        )

        with pytest.raises(ValueError):
            complete_onboarding(session, user)

        assert user.onboarding_step == 5
        assert user.onboarding_completed_at is None


def test_onboarding_completion_rejects_fewer_than_three_unique_interests(factory):
    with factory() as session:
        user = session.get(User, 1)
        update_onboarding(
            session,
            user,
            {
                "step": 5,
                "nickname": "小紫",
                "major": "软件工程",
                "grade": "大二",
                "interests": ["人工智能", "人工智能", "羽毛球"],
            },
        )

        with pytest.raises(ValueError, match="至少选择三个兴趣"):
            complete_onboarding(session, user)

        assert user.onboarding_step == 5
        assert user.onboarding_completed_at is None


def test_onboarding_completion_is_idempotent(factory):
    with factory() as session:
        user = session.get(User, 1)
        update_onboarding(
            session,
            user,
            {
                "step": 5,
                "nickname": "小紫",
                "major": "软件工程",
                "grade": "大二",
                "interests": ["人工智能", "产品设计", "羽毛球"],
            },
        )

        first = complete_onboarding(session, user)
        completed_at = user.onboarding_completed_at
        second = complete_onboarding(session, user)

        assert first["onboarding_completed"] is True
        assert second["onboarding_completed"] is True
        assert user.onboarding_step == 6
        assert user.onboarding_completed_at == completed_at


def test_auth_user_payload_reuses_onboarding_serialization(factory):
    with factory() as session:
        user = session.get(User, 1)
        update_onboarding(
            session,
            user,
            {"step": 2, "bio": "  想找长期队友  ", "skills": [" Python ", "Python"]},
        )

        auth_payload = _user_to_dict(user)
        onboarding_payload = onboarding_to_dict(user)

        assert {key: auth_payload[key] for key in onboarding_payload} == onboarding_payload


def test_onboarding_endpoints_require_authentication():
    app = FastAPI()
    app.include_router(auth_api.router)

    with TestClient(app) as test_client:
        response = test_client.get("/auth/onboarding")

    assert response.status_code == 401


def test_onboarding_get_and_patch_resume_the_authenticated_users_draft(client, factory):
    response = client.patch(
        "/auth/onboarding",
        json={
            "step": 3,
            "nickname": "  小紫  ",
            "major": " 软件工程 ",
            "grade": " 大二 ",
            "interests": ["人工智能", "产品设计", "人工智能", "羽毛球"],
        },
    )
    resumed = client.get("/auth/onboarding")

    assert response.status_code == 200
    assert response.json()["data"]["onboarding_step"] == 3
    assert resumed.json()["data"]["nickname"] == "小紫"
    assert resumed.json()["data"]["interests"] == ["人工智能", "产品设计", "羽毛球"]
    with factory() as session:
        assert session.get(User, 1).onboarding_step == 3


def test_onboarding_complete_returns_service_validation_without_committing(
    client, factory
):
    before = client.patch(
        "/auth/onboarding",
        json={"step": 4, "nickname": "小紫", "major": "软件工程", "grade": "大二"},
    )
    response = client.post("/auth/onboarding/complete")

    assert before.status_code == 200
    assert response.status_code == 400
    assert response.json() == {"detail": "至少选择三个兴趣"}
    with factory() as session:
        user = session.get(User, 1)
        assert user.onboarding_step == 4
        assert user.onboarding_completed_at is None


def test_onboarding_complete_commits_once_and_is_idempotent(client, factory):
    client.patch(
        "/auth/onboarding",
        json={
            "step": 5,
            "nickname": "小紫",
            "major": "软件工程",
            "grade": "大二",
            "interests": ["人工智能", "产品设计", "羽毛球"],
        },
    )

    first = client.post("/auth/onboarding/complete")
    with factory() as session:
        completed_at = session.get(User, 1).onboarding_completed_at
    second = client.post("/auth/onboarding/complete")

    assert first.status_code == 200
    assert first.json()["data"]["onboarding_completed"] is True
    assert second.status_code == 200
    with factory() as session:
        user = session.get(User, 1)
        assert user.onboarding_step == 6
        assert user.onboarding_completed_at == completed_at


def test_onboarding_complete_returns_the_authoritative_auth_user(client):
    client.patch(
        "/auth/onboarding",
        json={
            "step": 5,
            "nickname": "小紫",
            "major": "软件工程",
            "grade": "大二",
            "interests": ["人工智能", "产品设计", "羽毛球"],
        },
    )

    response = client.post("/auth/onboarding/complete")
    user = response.json()["data"]

    assert response.status_code == 200
    assert {
        "id",
        "email",
        "auth_status",
        "site_role",
        "account_status",
        "nickname",
        "major",
        "grade",
        "interests",
        "onboarding_step",
        "onboarding_completed",
    } <= set(user)
    assert user["id"] == "1"
    assert user["email"] == "student@smail.nju.edu.cn"
    assert user["auth_status"] == "unverified"
    assert user["site_role"] == "student"
    assert user["account_status"] == "active"
    assert user["nickname"] == "小紫"
    assert user["interests"] == ["人工智能", "产品设计", "羽毛球"]
    assert user["onboarding_step"] == 6
    assert user["onboarding_completed"] is True


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", "/auth/onboarding", None),
        ("patch", "/auth/onboarding", {"step": 2}),
        ("post", "/auth/onboarding/complete", None),
    ],
)
def test_onboarding_endpoints_return_404_for_missing_users(
    factory, monkeypatch, method, path, json_body
):
    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[current_user_id] = lambda: "999"
    monkeypatch.setattr(auth_api, "get_session", factory)

    with TestClient(app) as test_client:
        response = test_client.request(method, path, json=json_body)

    assert response.status_code == 404
    assert response.json() == {"detail": "用户不存在"}
