from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import agent
from storage.database.models import User
from storage.database.shared.model import Base


def _session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    session.add(
        User(
            id=1,
            email="student@smail.nju.edu.cn",
            password_hash="hash",
            nickname="同学",
            auth_status="verified",
        )
    )
    session.commit()
    session.close()
    return factory


def test_blocked_user_turn_does_not_call_ai_and_preserves_the_safe_draft(monkeypatch):
    factory = _session_factory()
    monkeypatch.setattr(agent, "get_session", factory)
    monkeypatch.setattr(
        agent,
        "invoke_tool",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("AI must not be called")),
    )
    previous_draft = {
        "activity_name": "羽毛球",
        "target_members": 2,
        "needed_roles": [],
        "weekly_hours": "周日下午",
        "school_scope": "体育馆",
        "deadline": "",
        "description": "",
    }
    field_states = {"activity_name": {"value": "羽毛球", "status": "confirmed"}}

    result = agent.post_draft(
        {
            "message": "约女同学去宾馆房间单独见面",
            "draft": previous_draft,
            "field_states": field_states,
            "kind": "casual_invitation",
        },
        "1",
    )

    assert result["code"] == 0
    assert result["data"]["blocked"] is True
    assert result["data"]["moderation"]["action"] == "block"
    assert result["data"]["draft"] == previous_draft
    assert result["data"]["field_states"] == field_states
    assert result["data"]["is_complete"] is False
    assert result["data"]["reply"] != "AI 服务不可用"


def test_unsafe_ai_output_is_rejected_and_previous_draft_is_restored(monkeypatch):
    factory = _session_factory()
    monkeypatch.setattr(agent, "get_session", factory)
    previous_draft = {"activity_name": "自习", "target_members": 2, "description": "图书馆学习"}
    monkeypatch.setattr(
        agent,
        "invoke_tool",
        lambda *_args, **_kwargs: json.dumps(
            {
                "reply": "信息齐全，加微信 abc_12345",
                "draft": {**previous_draft, "description": "加微信 abc_12345"},
                "field_states": {"description": {"value": "加微信 abc_12345", "status": "confirmed"}},
                "is_complete": True,
            },
            ensure_ascii=False,
        ),
    )

    result = agent.post_draft(
        {"message": "周末一起自习", "draft": previous_draft, "kind": "casual_invitation"},
        "1",
    )

    assert result["data"]["blocked"] is True
    assert result["data"]["moderation"]["action"] == "revise"
    assert result["data"]["draft"] == previous_draft
    assert result["data"]["is_complete"] is False
    assert "abc_12345" not in result["data"]["reply"]


def test_safe_user_turn_still_calls_ai(monkeypatch):
    factory = _session_factory()
    monkeypatch.setattr(agent, "get_session", factory)
    called = {"value": False}

    def fake_invoke(_tool, _payload):
        called["value"] = True
        return json.dumps(
            {
                "reply": "还需要补充活动地点。",
                "draft": {"activity_name": "羽毛球", "target_members": 2},
                "field_states": {},
                "is_complete": False,
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(agent, "invoke_tool", fake_invoke)

    result = agent.post_draft(
        {"message": "周末找一位同学打羽毛球", "kind": "casual_invitation"},
        "1",
    )

    assert called["value"] is True
    assert result["data"]["reply"] == "还需要补充活动地点。"
    assert result["data"].get("blocked") is not True
