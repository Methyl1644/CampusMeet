import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.database.models.post import Post
from storage.database.models.team import Team, TeamMember
from storage.database.models.user import User
from storage.database.shared.model import Base
from tools import ai_tools


CANONICAL_WORKFLOW_KEYS = (
    "COZE_WORKFLOW_POST_DRAFT",
    "COZE_WORKFLOW_CLASSIFY_REVIEW",
    "COZE_WORKFLOW_MATCH",
    "COZE_WORKFLOW_TEAM_PLAN",
)


def _disable_coze(monkeypatch):
    monkeypatch.delenv("COZE_API_TOKEN", raising=False)
    for key in CANONICAL_WORKFLOW_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    ("tool", "payload", "workflow_key"),
    [
        (ai_tools.ai_post_draft, {"message": "想参加美赛", "draft": "", "user_skills": "Python"}, "COZE_WORKFLOW_POST_DRAFT"),
        (ai_tools.ai_classify_review, {"post_title": "美赛招募", "post_description": "招募两名队友"}, "COZE_WORKFLOW_CLASSIFY_REVIEW"),
        (ai_tools.ai_match_teammates, {"post_id": "1"}, "COZE_WORKFLOW_MATCH"),
        (ai_tools.ai_team_plan, {"team_id": "1"}, "COZE_WORKFLOW_TEAM_PLAN"),
    ],
)
def test_each_ai_tool_honors_its_canonical_coze_environment_key(monkeypatch, tool, payload, workflow_key):
    """A configured canonical key must use Coze instead of entering the local fallback."""

    class Response:
        @staticmethod
        def json():
            return {"code": 0, "data": json.dumps({"source": "coze"})}

    for key in CANONICAL_WORKFLOW_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("COZE_API_TOKEN", "test-token")
    monkeypatch.setenv(workflow_key, "workflow-123")
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: Response())
    monkeypatch.setattr(ai_tools, "_call_llm", lambda *args, **kwargs: pytest.fail("unexpected LLM fallback"))
    monkeypatch.setattr(ai_tools, "get_session", lambda: pytest.fail("unexpected database fallback"))

    assert json.loads(tool.invoke(payload)) == {"source": "coze"}


def test_post_draft_falls_back_to_llm_without_coze_configuration(monkeypatch):
    _disable_coze(monkeypatch)
    monkeypatch.setattr(
        ai_tools,
        "_call_llm",
        lambda *args, **kwargs: json.dumps(
            {
                "reply": "请补充截止日期",
                "draft": {"activity_name": "美赛", "deadline": ""},
                "is_complete": False,
            },
            ensure_ascii=False,
        ),
    )

    result = json.loads(
        ai_tools.ai_post_draft.invoke({"message": "想参加美赛", "draft": "", "user_skills": "Python"})
    )

    assert result == {
        "reply": "请补充截止日期",
        "draft": {"activity_name": "美赛", "deadline": ""},
        "is_complete": False,
    }


def test_classify_review_falls_back_to_llm_without_coze_configuration(monkeypatch):
    _disable_coze(monkeypatch)
    monkeypatch.setattr(
        ai_tools,
        "_call_llm",
        lambda *args, **kwargs: json.dumps(
            {
                "main_category": "竞赛与项目",
                "tags": ["数学建模"],
                "risk_level": "low",
                "suggestions": ["补充截止日期"],
            },
            ensure_ascii=False,
        ),
    )

    result = json.loads(
        ai_tools.ai_classify_review.invoke({"post_title": "美赛招募", "post_description": "需要编程队友"})
    )

    assert result == {
        "main_category": "竞赛与项目",
        "tags": ["数学建模"],
        "risk_level": "low",
        "suggestions": ["补充截止日期"],
    }


@pytest.fixture
def database_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_match_falls_back_to_database_and_llm_without_coze_configuration(
    monkeypatch, database_session_factory
):
    session = database_session_factory()
    session.add_all(
        [
            Post(
                id=1,
                title="美赛招募",
                description="需要英文写作队友",
                main_category="竞赛与项目",
                activity_name="美赛",
                target_members=3,
                needed_roles=["英文写作"],
                author_id=1,
            ),
            User(
                id=1,
                email="owner@example.com",
                password_hash="hash",
                nickname="小王",
                skills=["Python"],
                auth_status="campus_verified",
            ),
            User(
                id=2,
                email="candidate@example.com",
                password_hash="hash",
                nickname="小李",
                major="英语",
                grade="大三",
                skills=["英文写作"],
                auth_status="campus_verified",
            ),
        ]
    )
    session.commit()
    session.close()

    _disable_coze(monkeypatch)
    monkeypatch.setattr(ai_tools, "get_session", database_session_factory)
    monkeypatch.setattr(
        ai_tools,
        "_call_llm",
        lambda *args, **kwargs: json.dumps(
            {"matches": [{"user_id": "2", "score": 92, "reason": "英文写作能力匹配"}]},
            ensure_ascii=False,
        ),
    )

    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert result == {
        "success": True,
        "matches": [{"user_id": "2", "score": 92, "reason": "英文写作能力匹配"}],
    }


def test_team_plan_falls_back_to_database_and_persists_plan_without_coze_configuration(
    monkeypatch, database_session_factory
):
    session = database_session_factory()
    session.add_all(
        [
            Post(
                id=1,
                title="美赛招募",
                description="完成数学建模比赛",
                main_category="竞赛与项目",
                activity_name="美赛",
                target_members=2,
                needed_roles=["建模", "写作"],
                author_id=1,
            ),
            Team(id=1, post_id=1, activity_name="美赛"),
            TeamMember(id=1, team_id=1, user_id=1, suggested_role="建模"),
            User(
                id=1,
                email="member@example.com",
                password_hash="hash",
                nickname="小王",
                major="数学",
                grade="大三",
                skills=["Python", "建模"],
                auth_status="campus_verified",
            ),
        ]
    )
    session.commit()
    session.close()

    expected_plan = {
        "division_of_labor": [{"role": "建模", "responsibilities": "建立模型", "member_id": "1"}],
        "meeting_agenda": [{"id": "a1", "content": "确认题目", "done": False}],
        "task_list": [{"id": "t1", "title": "整理资料", "done": False}],
        "risk_reminders": ["确认截止日期"],
    }
    _disable_coze(monkeypatch)
    monkeypatch.setattr(ai_tools, "get_session", database_session_factory)
    monkeypatch.setattr(ai_tools, "_call_llm", lambda *args, **kwargs: json.dumps(expected_plan, ensure_ascii=False))

    result = json.loads(ai_tools.ai_team_plan.invoke({"team_id": "1"}))

    assert result == {"success": True, "team_plan": expected_plan, "message": "AI 成队规划已生成并保存"}
    verify_session = database_session_factory()
    stored_team = verify_session.get(Team, 1)
    assert stored_team.division_of_labor == expected_plan["division_of_labor"]
    assert stored_team.meeting_agenda == expected_plan["meeting_agenda"]
    assert stored_team.task_list == expected_plan["task_list"]
    assert stored_team.risk_reminders == expected_plan["risk_reminders"]
    verify_session.close()
