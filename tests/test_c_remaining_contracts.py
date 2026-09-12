import importlib
import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def test_database_url_takes_priority_over_pgdabase_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://database-url")
    monkeypatch.setenv("PGDATABASE_URL", "postgresql://pgdatabase-url")

    import storage.database.db as db

    assert db.get_db_url() == "postgresql://database-url"


def test_windows_only_blocking_dependencies_are_not_required():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]

    assert "pycairo==1.29.0" not in deps
    assert "dbus-python==1.3.2" not in deps
    assert "PyGObject==3.48.2" not in deps


def test_coze_schemas_match_backend_workflow_payloads():
    post_input = json.loads(Path("coze/schemas/post_draft.input.json").read_text(encoding="utf-8"))
    team_input = json.loads(Path("coze/schemas/team_plan.input.json").read_text(encoding="utf-8"))
    team_output = json.loads(Path("coze/schemas/team_plan.output.json").read_text(encoding="utf-8"))

    assert set(post_input["required"]) == {"message", "kind", "field_states", "candidate_tags"}
    assert "user_text" not in post_input["properties"]
    assert team_input["required"] == ["team_id"]
    assert set(team_output["required"]) == {
        "division_of_labor",
        "meeting_agenda",
        "task_list",
        "risk_reminders",
    }


def test_main_configures_cors_for_vite_and_auto_creates_tables():
    main_source = Path("src/main.py").read_text(encoding="utf-8")

    assert "CORSMiddleware" in main_source
    assert "allow_origins=get_allowed_origins()" in main_source
    assert "Base.metadata.create_all(engine)" in main_source


def test_frontend_serializes_tag_filters_as_backend_comma_list():
    source = Path("apps/web/src/api/posts.ts").read_text(encoding="utf-8")

    assert "tags: params.tags?.join(',')" in source


def test_main_sets_a_windows_safe_coze_log_directory_before_sdk_imports():
    main_source = Path("src/main.py").read_text(encoding="utf-8")

    assert main_source.index("COZE_LOG_DIR") < main_source.index("import cozeloop")


def test_agent_runtime_is_optional_for_local_rest_api():
    from utils.runtime import should_start_agent_runtime

    assert should_start_agent_runtime({}) is False
    assert should_start_agent_runtime({"COZE_WORKLOAD_IDENTITY_API_KEY": "configured"}) is True
    assert should_start_agent_runtime({"ENABLE_AGENT_RUNTIME": "true"}) is True
    assert should_start_agent_runtime({"ENABLE_AGENT_RUNTIME": "false", "COZE_WORKLOAD_IDENTITY_API_KEY": "configured"}) is False


def test_classify_review_sends_cleaned_text_to_ai(monkeypatch):
    calls = {}

    class FakeTool:
        @staticmethod
        def invoke(payload):
            calls["payload"] = payload
            return json.dumps(
                {
                    "main_category": "竞赛与项目",
                    "tags": [],
                    "risk_level": "low",
                    "suggestions": [],
                },
                ensure_ascii=False,
            )

    fake_ai_tools = SimpleNamespace(
        ai_classify_review=FakeTool(),
        ai_match_teammates=FakeTool(),
        ai_post_draft=FakeTool(),
        ai_team_plan=FakeTool(),
    )
    monkeypatch.setitem(sys.modules, "tools.ai_tools", fake_ai_tools)

    import api.agent as agent

    importlib.reload(agent)
    monkeypatch.setattr(agent, "_require_verified_user", lambda *_: None)
    result = agent.classify_review(
        {"title": "美赛招募", "description": "联系微信 abcdef123456"},
        user_id="1",
    )

    assert result["code"] == 0
    assert calls["payload"]["post_title"] == "美赛招募"
    assert calls["payload"]["post_description"] != "联系微信 abcdef123456"
    assert "[联系方式已隐藏]" in calls["payload"]["post_description"]


def test_agent_match_returns_matches_object(monkeypatch):
    class MatchTool:
        @staticmethod
        def invoke(payload):
            assert payload == {"post_id": "1"}
            return json.dumps(
                {
                    "success": True,
                    "matches": [{"user_id": "2", "score": 87, "reason": "技能匹配"}],
                    "message": "ok",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("api.agent.ai_match_teammates", MatchTool())

    from api.agent import match

    monkeypatch.setattr("api.agent._require_post_owner", lambda *_: None)

    result = match({"post_id": "1"}, user_id="1")

    assert result == {
        "code": 0,
        "message": "ok",
        "data": {"matches": [{"user_id": "2", "score": 87, "reason": "技能匹配"}]},
    }


def test_agent_team_plan_returns_plan_without_team_plan_nesting(monkeypatch):
    plan = {
        "division_of_labor": [],
        "meeting_agenda": [],
        "task_list": [],
        "risk_reminders": [],
    }

    class TeamPlanTool:
        @staticmethod
        def invoke(payload):
            assert payload == {"team_id": "1"}
            return json.dumps({"success": True, "team_plan": plan, "message": "ok"}, ensure_ascii=False)

    monkeypatch.setattr("api.agent.ai_team_plan", TeamPlanTool())

    from api.agent import team_plan

    monkeypatch.setattr("api.agent._require_team_member", lambda *_: None)

    result = team_plan({"team_id": "1"}, user_id="1")

    assert result == {"code": 0, "message": "ok", "data": plan}
    assert "team_plan" not in result["data"]


def _agent_sessionmaker():
    from storage.database import models  # noqa: F401
    from storage.database.shared.model import Base

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_agent_match_requires_verified_post_owner(monkeypatch):
    from api import agent
    from storage.database.models import Post, User

    sessions = _agent_sessionmaker()
    with sessions() as session:
        owner = User(email="owner@example.com", password_hash="x", nickname="owner", auth_status="verified")
        stranger = User(email="stranger@example.com", password_hash="x", nickname="stranger", auth_status="verified")
        session.add_all([owner, stranger])
        session.flush()
        post = Post(
            title="test",
            main_category="校园生活",
            activity_name="test",
            target_members=2,
            author_id=owner.id,
        )
        session.add(post)
        session.commit()
        post_id = post.id
        stranger_id = stranger.id

    monkeypatch.setattr(agent, "get_session", sessions)
    with pytest.raises(HTTPException) as exc:
        agent.match({"post_id": str(post_id)}, user_id=str(stranger_id))

    assert exc.value.status_code == 403


def test_agent_team_plan_requires_team_membership(monkeypatch):
    from api import agent
    from storage.database.models import Post, Team, User

    sessions = _agent_sessionmaker()
    with sessions() as session:
        owner = User(email="owner@example.com", password_hash="x", nickname="owner", auth_status="verified")
        stranger = User(email="stranger@example.com", password_hash="x", nickname="stranger", auth_status="verified")
        session.add_all([owner, stranger])
        session.flush()
        post = Post(
            title="test",
            main_category="校园生活",
            activity_name="test",
            target_members=2,
            author_id=owner.id,
        )
        session.add(post)
        session.flush()
        team = Team(post_id=post.id, activity_name="test")
        session.add(team)
        session.commit()
        team_id = team.id
        stranger_id = stranger.id

    monkeypatch.setattr(agent, "get_session", sessions)
    with pytest.raises(HTTPException) as exc:
        agent.team_plan({"team_id": str(team_id)}, user_id=str(stranger_id))

    assert exc.value.status_code == 403
