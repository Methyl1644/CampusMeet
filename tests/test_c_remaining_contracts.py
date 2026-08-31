import importlib
import json
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace


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


def test_main_configures_cors_for_vite_and_auto_creates_tables():
    main_source = Path("src/main.py").read_text(encoding="utf-8")

    assert "CORSMiddleware" in main_source
    assert "http://localhost:5173" in main_source
    assert "Base.metadata.create_all(engine)" in main_source


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
    result = agent.classify_review({"title": "美赛招募", "description": "联系微信 abcdef123456"})

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

    result = match({"post_id": "1"})

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

    result = team_plan({"team_id": "1"})

    assert result == {"code": 0, "message": "ok", "data": plan}
    assert "team_plan" not in result["data"]
