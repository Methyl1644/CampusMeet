from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.database.models import Post, Team, TeamMember, User, UserBlock
from storage.database.shared.model import Base
from tools import ai_tools


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(
                    id=1,
                    email="owner@nju.edu.cn",
                    phone="13800138000",
                    wechat="owner-secret",
                    password_hash="hash",
                    nickname="owner",
                    auth_status="verified",
                    skills=["Python"],
                ),
                User(
                    id=2,
                    email="candidate@nju.edu.cn",
                    phone="13900139000",
                    wechat="candidate-secret",
                    password_hash="hash",
                    nickname="candidate",
                    auth_status="verified",
                    major="软件工程",
                    grade="大三",
                    skills=["Python", "算法"],
                    interests=["竞赛与项目"],
                    looking_for=["竞赛队友"],
                    availability={"weekend_daytime": True, "weekly_hours": "每周 4-6 小时"},
                    profile_visibility={
                        "major": False,
                        "grade": True,
                        "interests": True,
                        "skills": True,
                        "availability": True,
                        "matching": True,
                    },
                ),
                User(
                    id=3,
                    email="blocked@nju.edu.cn",
                    password_hash="hash",
                    nickname="blocked",
                    auth_status="verified",
                    skills=["Python"],
                ),
            ]
        )
        post = Post(
            id=1,
            title="编程竞赛",
            description="需要 Python 和算法队友",
            main_category="竞赛与项目",
            activity_name="编程竞赛",
            needed_roles=["开发"],
            target_members=3,
            author_id=1,
        )
        session.add(post)
        session.flush()
        session.add(UserBlock(blocker_id=1, blocked_id=3))
        team = Team(id=1, post_id=1, owner_id=1, activity_name="编程竞赛")
        session.add(team)
        session.flush()
        session.add_all(
            [
                TeamMember(team_id=1, user_id=1, member_role="owner", suggested_role="队长"),
            ]
        )
        session.commit()
    return factory


def test_deployed_match_receives_only_controlled_candidates_and_validates_output(monkeypatch):
    factory = _factory()
    captured = {}
    monkeypatch.setattr(ai_tools, "get_session", factory)
    monkeypatch.setenv("COZE_MATCH_API_URL", "https://match.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret")

    def fake_call(key, parameters):
        captured["key"] = key
        captured["parameters"] = parameters
        return {
            "matches": [
                {"user_id": "999", "score": 100, "reason": "越权"},
                {"user_id": "2", "score": 130, "reason": "技能匹配"},
                {"user_id": "2", "score": 80, "reason": "重复"},
            ]
        }

    monkeypatch.setattr(ai_tools, "_try_coze_deployed_api", fake_call)
    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert len(result["matches"]) == 1
    assert result["matches"][0]["user_id"] == "2"
    assert result["matches"][0]["score"] == 100
    assert result["matches"][0]["reason"] == "技能匹配"
    assert result["matches"][0]["nickname"] == "candidate"
    assert captured["key"] == "COZE_MATCH_API_URL"
    serialized = json.dumps(captured["parameters"], ensure_ascii=False)
    assert "candidate@nju.edu.cn" not in serialized
    assert "candidate-secret" not in serialized
    assert "13900139000" not in serialized
    assert '"user_id": "3"' not in serialized
    candidate = captured["parameters"]["candidates"][0]
    assert "major" not in candidate
    assert "grade" not in candidate
    assert candidate["skills"] == ["Python", "算法"]
    assert candidate["interests"] == ["竞赛与项目"]
    assert candidate["availability"]["weekly_hours"] == "每周 4-6 小时"


def test_match_excludes_existing_team_members(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    with factory() as session:
        session.add(TeamMember(team_id=1, user_id=2, member_role="member"))
        session.commit()

    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert result["success"] is True
    assert result["matches"] == []


def test_match_excludes_inactive_accounts(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    with factory() as session:
        candidate = session.get(User, 2)
        candidate.account_status = "deactivated"
        session.commit()

    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert result["success"] is True
    assert result["matches"] == []


def test_match_excludes_users_who_did_not_opt_in(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    with factory() as session:
        candidate = session.get(User, 2)
        candidate.profile_visibility = {
            **candidate.profile_visibility,
            "matching": False,
        }
        session.commit()

    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert result["success"] is True
    assert result["matches"] == []
    assert "暂无" in result["message"]


def test_deployed_team_plan_is_validated_and_persisted(monkeypatch):
    factory = _factory()
    captured = {}
    monkeypatch.setattr(ai_tools, "get_session", factory)
    monkeypatch.setenv("COZE_TEAM_PLAN_API_URL", "https://plan.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret")

    def fake_call(key, parameters):
        captured["parameters"] = parameters
        return {
            "division_of_labor": [
                {"role": "队长", "responsibilities": "协调", "member_id": "1"},
                {"role": "越权", "responsibilities": "无效", "member_id": "999"},
            ],
            "meeting_agenda": [{"id": "a1", "content": "确认目标", "done": False}],
            "task_list": [
                {"id": "t1", "title": "搭建仓库", "done": False},
                {"id": "t1", "title": "重复任务", "done": False},
            ],
            "risk_reminders": ["注意截止时间"],
        }

    monkeypatch.setattr(ai_tools, "_try_coze_deployed_api", fake_call)
    result = json.loads(ai_tools.ai_team_plan.invoke({"team_id": "1"}))

    assert result["success"] is True
    assert result["team_plan"]["division_of_labor"] == [
        {"role": "队长", "responsibilities": "协调", "member_id": "1"}
    ]
    assert len(result["team_plan"]["task_list"]) == 1
    serialized = json.dumps(captured["parameters"], ensure_ascii=False)
    assert "@nju.edu.cn" not in serialized
    assert "secret" not in serialized
    with factory() as session:
        team = session.get(Team, 1)
        assert team.task_list == result["team_plan"]["task_list"]
        assert team.division_of_labor == result["team_plan"]["division_of_labor"]


def test_deployed_team_plan_bounds_imported_tasks_as_input_grows(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    monkeypatch.setenv("COZE_TEAM_PLAN_API_URL", "https://plan.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret")
    imported_tasks = [
        {"id": f"task-{index}", "title": f"导入任务 {index}", "done": False}
        for index in range(80)
    ]
    monkeypatch.setattr(
        ai_tools,
        "_try_coze_deployed_api",
        lambda *_args: {
            "division_of_labor": [],
            "meeting_agenda": [],
            "task_list": imported_tasks,
            "risk_reminders": [],
        },
    )

    result = json.loads(ai_tools.ai_team_plan.invoke({"team_id": "1"}))

    assert result["success"] is True
    assert len(result["team_plan"]["task_list"]) == 12
    assert result["team_plan"]["task_list"][-1]["id"] == "task-11"
    with factory() as session:
        assert len(session.get(Team, 1).task_list) == 12


def test_deployed_team_plan_returns_the_byte_bounded_persisted_tasks(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    monkeypatch.setenv("COZE_TEAM_PLAN_API_URL", "https://plan.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret")
    supplementary_title = "🚀" * 120
    imported_tasks = [
        {"id": f"task-{index}", "title": supplementary_title, "done": False}
        for index in range(12)
    ]
    monkeypatch.setattr(
        ai_tools,
        "_try_coze_deployed_api",
        lambda *_args: {
            "division_of_labor": [],
            "meeting_agenda": [],
            "task_list": imported_tasks,
            "risk_reminders": [],
        },
    )

    result = json.loads(ai_tools.ai_team_plan.invoke({"team_id": "1"}))

    assert result["success"] is True
    assert len(result["team_plan"]["task_list"]) < 12
    with factory() as session:
        persisted = session.get(Team, 1).task_list
    assert result["team_plan"]["task_list"] == persisted


def test_malformed_match_output_uses_deterministic_candidate_fallback(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(ai_tools, "get_session", factory)
    monkeypatch.setenv("COZE_MATCH_API_URL", "https://match.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret")
    monkeypatch.setattr(ai_tools, "_try_coze_deployed_api", lambda *_args: {"matches": "invalid"})
    monkeypatch.setattr(ai_tools, "_call_llm", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))

    result = json.loads(ai_tools.ai_match_teammates.invoke({"post_id": "1"}))

    assert result["success"] is True
    assert result["matches"]
    assert result["matches"][0]["user_id"] == "2"
    assert result["matches"][0]["score"] <= 40
    assert "信息不足" in result["matches"][0]["reason"]
