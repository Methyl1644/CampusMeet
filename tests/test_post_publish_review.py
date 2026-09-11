import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import posts as posts_api
from services.content import seed_content_catalog
from storage.database.models import Post, PostTag, User
from storage.database.shared.model import Base
from tools import post_tools


def _review_result(*, risk_level: str = "low") -> dict:
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "main_category": "竞赛与项目",
            "tag_ids": ["skill_python", "activity_programming"],
            "unknown_concepts": [],
            "risk_level": risk_level,
            "suggestions": ["请勿发布押金或站外交易信息"] if risk_level == "high" else [],
            "tag_proposals": [],
        },
    }


def test_create_post_uses_classification_and_only_adds_new_ai_tags(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(posts_api, "classify_review", lambda *_args, **_kwargs: _review_result(risk_level="medium"), raising=False)

    def fake_invoke(_tool, payload):
        captured.update(payload)
        return json.dumps(
            {
                "success": True,
                "post": {"id": "10", "risk_level": "medium"},
                "message": "帖子发布成功，风险等级: medium",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(posts_api, "invoke_tool", fake_invoke)

    result = posts_api.create(
        {
            "title": "程序设计竞赛招募",
            "description": "需要一名 Python 队友",
            "activity_name": "程序设计竞赛",
            "target_members": 2,
            "tag_ids": ["skill_python"],
        },
        user_id="7",
    )

    assert result["data"]["risk_level"] == "medium"
    assert captured["main_category"] == "竞赛与项目"
    assert captured["tag_ids"] == "skill_python"
    assert captured["suggested_tag_ids"] == "activity_programming"
    assert captured["review_risk_level"] == "medium"


def test_create_post_rejects_high_risk_ai_review(monkeypatch):
    monkeypatch.setattr(posts_api, "classify_review", lambda *_args, **_kwargs: _review_result(risk_level="high"), raising=False)
    monkeypatch.setattr(
        posts_api,
        "invoke_tool",
        lambda *_args, **_kwargs: json.dumps({"success": True, "post": {"id": "10"}}),
    )

    with pytest.raises(HTTPException) as exc:
        posts_api.create(
            {
                "title": "课程作业代写",
                "description": "先交押金后加群",
                "target_members": 1,
            },
            user_id="7",
        )

    assert exc.value.status_code == 400
    assert "风险" in str(exc.value.detail)


def test_rejected_high_risk_post_does_not_create_tag_proposals(monkeypatch):
    from api import agent
    from storage.database.models import TagProposal

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        seed_content_catalog(session)
        user = User(
            email="student@nju.edu.cn",
            password_hash="hash",
            nickname="student",
            auth_status="verified",
        )
        session.add(user)
        session.commit()
        user_id = str(user.id)

    monkeypatch.setattr(agent, "get_session", sessions)
    monkeypatch.setattr(
        agent,
        "invoke_tool",
        lambda *_args, **_kwargs: json.dumps(
            {
                "main_category": "体育与健身",
                "tag_ids": [],
                "unknown_concepts": [
                    {"name": "定向越野", "category": "activity", "reason": "标签库暂未收录"}
                ],
                "risk_level": "high",
                "suggestions": ["删除押金信息"],
            },
            ensure_ascii=False,
        ),
    )

    with pytest.raises(HTTPException):
        posts_api.create(
            {"title": "定向越野招募", "description": "先交押金后加群", "target_members": 2},
            user_id=user_id,
        )

    with sessions() as session:
        assert session.execute(select(TagProposal)).scalars().all() == []


def test_successful_post_stores_sanitized_unknown_tag_proposals(monkeypatch):
    from api import agent
    from storage.database.models import TagProposal

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        seed_content_catalog(session)
        user = User(
            email="student@nju.edu.cn",
            password_hash="hash",
            nickname="student",
            auth_status="verified",
        )
        session.add(user)
        session.commit()
        user_id = str(user.id)

    monkeypatch.setattr(agent, "get_session", sessions)
    monkeypatch.setattr(
        agent,
        "invoke_tool",
        lambda *_args, **_kwargs: json.dumps(
            {
                "main_category": "体育与健身",
                "tag_ids": [],
                "unknown_concepts": [
                    {"name": "定向越野", "category": "activity", "reason": "标签库暂未收录"}
                ],
                "risk_level": "low",
                "suggestions": [],
            },
            ensure_ascii=False,
        ),
    )
    monkeypatch.setattr(
        posts_api,
        "invoke_tool",
        lambda *_args, **_kwargs: json.dumps(
            {"success": True, "post": {"id": "10", "risk_level": "low"}},
            ensure_ascii=False,
        ),
    )

    result = posts_api.create(
        {"title": "定向越野招募", "description": "周末找两名队友", "target_members": 2},
        user_id=user_id,
    )

    assert result["code"] == 0
    with sessions() as session:
        proposals = session.execute(select(TagProposal)).scalars().all()
        assert [(item.proposed_name, item.status) for item in proposals] == [("定向越野", "pending")]


def test_create_post_ignores_unknown_ai_category(monkeypatch):
    captured: dict = {}
    malformed_review = _review_result()
    malformed_review["data"]["main_category"] = "任意注入分类"
    monkeypatch.setattr(posts_api, "classify_review", lambda *_args, **_kwargs: malformed_review, raising=False)

    def fake_invoke(_tool, payload):
        captured.update(payload)
        return json.dumps({"success": True, "post": {"id": "10", "risk_level": "low"}}, ensure_ascii=False)

    monkeypatch.setattr(posts_api, "invoke_tool", fake_invoke)

    posts_api.create(
        {"title": "周末羽毛球搭子", "description": "仙林校区活动", "target_members": 2},
        user_id="7",
    )

    assert captured["main_category"] == "校园生活"


def test_create_post_uses_local_review_when_ai_service_is_unavailable(monkeypatch):
    captured: dict = {}

    def unavailable(*_args, **_kwargs):
        raise HTTPException(status_code=502, detail="AI service unavailable")

    def fake_invoke(_tool, payload):
        captured.update(payload)
        return json.dumps(
            {"success": True, "post": {"id": "10", "risk_level": "low"}},
            ensure_ascii=False,
        )

    monkeypatch.setattr(posts_api, "classify_review", unavailable, raising=False)
    monkeypatch.setattr(posts_api, "invoke_tool", fake_invoke)

    result = posts_api.create(
        {
            "title": "周末羽毛球搭子",
            "description": "仙林校区活动",
            "target_members": 2,
            "tag_ids": ["activity_badminton"],
        },
        user_id="7",
    )

    assert result["code"] == 0
    assert captured["main_category"] == "校园生活"
    assert captured["tag_ids"] == "activity_badminton"
    assert captured["suggested_tag_ids"] == ""
    assert captured["review_risk_level"] == "low"


def test_update_post_rechecks_ai_risk_before_saving(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        user = User(
            email="editor@nju.edu.cn",
            password_hash="hash",
            nickname="editor",
            auth_status="verified",
        )
        session.add(user)
        session.flush()
        post = Post(
            title="正常组队帖",
            description="招募队友",
            kind="casual_invitation",
            main_category="校园生活",
            activity_name="日常活动",
            target_members=2,
            author_id=user.id,
        )
        session.add(post)
        session.commit()
        post_id = post.id
        user_id = str(user.id)

    monkeypatch.setattr(posts_api, "get_session", sessions)
    monkeypatch.setattr(posts_api, "classify_review", lambda *_args, **_kwargs: _review_result(risk_level="high"), raising=False)

    with pytest.raises(HTTPException) as exc:
        posts_api.update(
            post_id,
            {"title": "课程作业代写", "description": "先交押金后加群"},
            user_id,
        )

    assert exc.value.status_code == 400
    with sessions() as session:
        unchanged = session.get(Post, post_id)
        assert unchanged.title == "正常组队帖"
        assert unchanged.description == "招募队友"


def test_create_post_tool_persists_review_risk_and_ai_tag_source(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        seed_content_catalog(session)
        user = User(
            email="student@nju.edu.cn",
            password_hash="hash",
            nickname="student",
            auth_status="verified",
        )
        session.add(user)
        session.commit()
        user_id = str(user.id)

    monkeypatch.setattr(post_tools, "get_session", sessions)
    result = json.loads(
        post_tools.create_post.invoke(
            {
                "user_id": user_id,
                "title": "程序设计竞赛招募",
                "description": "需要一名 Python 队友",
                "main_category": "竞赛与项目",
                "activity_name": "程序设计竞赛",
                "target_members": 2,
                "needed_roles": "开发",
                "tag_ids": "skill_python",
                "suggested_tag_ids": "activity_programming",
                "review_risk_level": "medium",
            }
        )
    )

    assert result["success"] is True
    assert result["post"]["risk_level"] == "medium"
    with sessions() as session:
        post = session.execute(select(Post)).scalar_one()
        tag_sources = {
            item.tag_id: item.source
            for item in session.execute(select(PostTag).where(PostTag.post_id == post.id)).scalars()
        }
    assert tag_sources == {
        "skill_python": "user",
        "activity_programming": "ai",
    }


def test_create_post_tool_rejects_high_review_risk_before_persisting(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        user = User(
            email="student@nju.edu.cn",
            password_hash="hash",
            nickname="student",
            auth_status="verified",
        )
        session.add(user)
        session.commit()
        user_id = str(user.id)

    monkeypatch.setattr(post_tools, "get_session", sessions)
    result = json.loads(
        post_tools.create_post.invoke(
            {
                "user_id": user_id,
                "title": "课程作业代写",
                "description": "先交押金后加群",
                "main_category": "校园生活",
                "activity_name": "课程协作",
                "target_members": 1,
                "needed_roles": "",
                "review_risk_level": "high",
            }
        )
    )

    assert result["success"] is False
    assert "风险" in result["message"]
    with sessions() as session:
        assert session.execute(select(Post)).scalars().all() == []
