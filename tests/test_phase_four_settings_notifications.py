from __future__ import annotations

import datetime
import importlib
import importlib.util

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import notifications as notifications_api
from api.common import current_user_id
from storage.database.models import Notification, User
from storage.database.shared.model import Base


PREFERENCE_DEFAULTS = {
    "applications": True,
    "teams": True,
    "moderation": True,
    "deadlines": True,
    "messages": True,
}


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
        session.add(User(id=1, email="member@smail.nju.edu.cn", password_hash="hash", nickname="成员"))
        session.flush()
        session.add_all(
            [
                Notification(
                    id=index,
                    user_id=1,
                    event_type="message.created",
                    title=f"通知 {index}",
                    body="内容",
                    target_type="conversation",
                    target_id=str(index),
                    dedupe_key=f"notification:{index}",
                    created_at=datetime.datetime(2026, 9, 13, 12, index % 60, tzinfo=datetime.timezone.utc),
                )
                for index in range(1, 46)
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
    app.include_router(notifications_api.router, prefix="/api")
    monkeypatch.setattr(notifications_api, "get_session", factory)
    app.dependency_overrides[current_user_id] = lambda: "1"
    with TestClient(app) as test_client:
        yield test_client


def test_user_notification_preferences_have_bounded_defaults(factory):
    assert "notification_preferences" in User.__table__.columns
    with factory() as session:
        assert session.get(User, 1).notification_preferences == PREFERENCE_DEFAULTS


@pytest.mark.parametrize(
    "preferences",
    [
        {"messages": True},
        {**PREFERENCE_DEFAULTS, "messages": "yes"},
        {**PREFERENCE_DEFAULTS, "unknown": True},
    ],
)
def test_notification_preference_database_constraint_rejects_invalid_shapes(factory, preferences):
    with factory() as session:
        session.get(User, 1).notification_preferences = preferences
        with pytest.raises(IntegrityError):
            session.commit()


def test_settings_get_and_patch_normalize_partial_preferences(client, factory):
    initial = client.get("/api/me/settings")

    assert initial.status_code == 200
    assert initial.json()["data"]["notification_preferences"] == PREFERENCE_DEFAULTS

    response = client.patch(
        "/api/me/settings",
        json={
            "profile_visibility": {"contact": True},
            "notification_preferences": {"messages": False},
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["profile_visibility"]["contact"] is True
    assert response.json()["data"]["notification_preferences"] == {
        **PREFERENCE_DEFAULTS,
        "messages": False,
    }
    with factory() as session:
        user = session.get(User, 1)
        assert user.notification_preferences["messages"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"notification_preferences": {"unknown": True}},
        {"notification_preferences": {"messages": 1}},
        {"profile_visibility": {"contact": "yes"}},
        {"unknown": "x" * 5000},
    ],
)
def test_settings_reject_unknown_non_boolean_and_oversized_payloads(client, payload):
    assert client.patch("/api/me/settings", json=payload).status_code == 422


def test_notification_pagination_is_bounded_and_deterministic(client):
    response = client.get("/api/notifications?page=1&page_size=40")

    assert response.status_code == 200
    assert response.json()["data"]["page_size"] == 40
    assert [item["id"] for item in response.json()["data"]["list"][:2]] == ["45", "44"]
    assert client.get("/api/notifications?page_size=41").status_code == 422
    assert client.get("/api/notifications?page=0").status_code == 422


def test_notification_read_is_idempotent_and_returns_current_unread_count(client):
    first = client.post("/api/notifications/45/read")
    second = client.post("/api/notifications/45/read")

    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["unread_count"] == 44
    assert second.json()["data"]["unread_count"] == 44
    assert first.json()["data"]["read_at"] == second.json()["data"]["read_at"]


def test_notification_read_all_is_idempotent_and_returns_current_unread_count(client):
    first = client.post("/api/notifications/read-all")
    second = client.post("/api/notifications/read-all")

    assert first.json()["data"] == {"updated": 45, "unread_count": 0}
    assert second.json()["data"] == {"updated": 0, "unread_count": 0}
