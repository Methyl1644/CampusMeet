from __future__ import annotations

import pytest
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import applications, messages, teams
from api.common import current_user_id
from services.observability import install_observability
from storage.database.models import Application, Conversation, Notification, Post, TeamMember, User
from storage.database.shared.model import Base
from tools import application_tools, message_tools, team_tools


ORIGIN = "https://campusmate-web.onrender.com"


@pytest.fixture
def http_flow(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'application-http.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            User(id=number, email=f"student{number}@nju.edu.cn", password_hash="test",
                 nickname=f"student{number}", auth_status="verified", wechat=f"student_{number}")
            for number in (1, 2, 3)
        ])
        session.add(Post(id=3, author_id=1, title="Football", description="Campus game",
                         main_category="校园生活", activity_name="Football",
                         target_members=11, current_members=1, needed_roles=[], deadline="明天"))
        session.commit()
    for module in (application_tools, message_tools, team_tools):
        monkeypatch.setattr(module, "get_session", factory)

    app = FastAPI()
    install_observability(app)
    app.add_middleware(CORSMiddleware, allow_origins=[ORIGIN], allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    for router in (applications.router, messages.router, teams.router):
        app.include_router(router, prefix="/api")

    # Only identity is supplied by the fixture; schemas, tools and persistence are real.
    def test_identity(x_test_user: str = Header(default="2")) -> str:
        return x_test_user

    app.dependency_overrides[current_user_id] = test_identity
    with TestClient(app, raise_server_exceptions=False, headers={"Origin": ORIGIN}) as client:
        yield client, factory
    engine.dispose()


def payload(post_id):
    return {"post_id": post_id, "role_wanted": "不限角色", "experience": "1年",
            "available_time": "每周2小时", "reason": "想参加", "questions": []}


def ok(response):
    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.json()["code"] == 0
    return response.json()["data"]


@pytest.mark.parametrize("post_id", [3, "3"])
def test_http_application_chat_confirmation_and_contacts(http_flow, post_id):
    client, factory = http_flow
    owner = {"X-Test-User": "1"}
    created = ok(client.post("/api/applications", json=payload(post_id)))
    assert created["status"] == "pending"
    duplicate = ok(client.post("/api/applications", json=payload(post_id)))
    assert duplicate["id"] == created["id"]
    received = ok(client.get("/api/applications", params={"post_id": "3"}, headers=owner))
    assert received["list"][0]["id"] == created["id"]
    assert ok(client.get("/api/applications/my"))["list"][0]["id"] == created["id"]

    accepted = ok(client.post(f"/api/applications/{created['id']}/accept", headers=owner))
    conversation_id = accepted["conversation_id"]
    repeated = ok(client.post(f"/api/applications/{created['id']}/accept", headers=owner))
    assert repeated["conversation_id"] == conversation_id
    for headers in ({}, owner):
        conversation = ok(client.get("/api/messages/conversations", headers=headers))["list"][0]
        assert conversation["id"] == conversation_id
        assert conversation["contact_unlocked"] is False
        assert "wechat" not in conversation["other_user"]
    path = f"/api/messages/{conversation_id}"
    sent = ok(client.post(f"{path}/send", json={"content": "周末一起参加吧"}))
    assert sent["content"] == "周末一起参加吧"
    assert ok(client.get(path, headers=owner))["list"][0]["id"] == sent["id"]
    ok(client.post(f"{path}/send", json={"content": "好的，周末见"}, headers=owner))
    assert len(ok(client.get(path))["list"]) == 2
    assert client.get(path, headers={"X-Test-User": "3"}).status_code == 400

    first_confirmation = ok(client.post(f"{path}/confirm-team", headers=owner))
    assert first_confirmation["contact_unlocked"] is False
    confirmed = ok(client.post(f"{path}/confirm-team"))
    assert confirmed["contact_unlocked"] is True
    team = ok(client.get(f"/api/teams/{confirmed['team_id']}"))
    assert {item["wechat"] for item in team["contact_info"]} == {"student_1", "student_2"}
    with factory() as session:
        assert len(session.scalars(select(Application)).all()) == 1
        assert len(session.scalars(select(Conversation)).all()) == 1
        assert len(session.scalars(select(TeamMember)).all()) == 2
        assert session.get(Post, 3).current_members == 2
        events = set(session.scalars(select(Notification.event_type)).all())
        assert {"application.created", "application.accepted", "message.created", "team.confirmed"} <= events


def test_http_application_keeps_validation_and_business_errors(http_flow):
    client, _ = http_flow
    invalid = client.post("/api/applications", json=payload(0))
    assert invalid.status_code == 422
    assert invalid.headers["access-control-allow-origin"] == ORIGIN
    own_post = client.post("/api/applications", json=payload(3), headers={"X-Test-User": "1"})
    assert own_post.status_code == 400
    assert "自己的帖子" in own_post.json()["message"]
