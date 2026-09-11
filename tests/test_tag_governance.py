import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from services.content import seed_content_catalog, tag_suggestions
from storage.database.models import AuditLog, Tag, TagAlias, User
from storage.database.shared.model import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(email: str, role: str = "student") -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role=role,
    )


def test_seed_catalog_covers_common_activity_skill_role_level_and_audience_tags():
    with _session() as session:
        seed_content_catalog(session)
        tags = session.execute(select(Tag).where(Tag.active.is_(True))).scalars().all()

        assert {tag.category for tag in tags} == {"activity", "skill", "role", "level", "audience"}
        assert len(tags) >= 70
        names = {tag.canonical_name for tag in tags}
        assert {
            "程序设计",
            "电子设计",
            "志愿服务",
            "足球",
            "Python",
            "数据分析",
            "队长",
            "文案",
            "省级",
            "研究生",
        }.issubset(names)


def test_ambiguous_legacy_alias_is_deactivated_instead_of_forcing_one_activity():
    with _session() as session:
        seed_content_catalog(session)

        assert tag_suggestions(session, "打球") == []
        alias = session.execute(
            select(TagAlias).where(TagAlias.normalized_alias == "打球")
        ).scalar_one_or_none()
        assert alias is None or alias.active is False


def test_unknown_tag_proposal_is_pending_and_repeated_observations_increment_it():
    from services.tag_governance import submit_tag_proposal
    from storage.database.models import TagProposal

    with _session() as session:
        seed_content_catalog(session)
        user = _user("student@nju.edu.cn")
        session.add(user)
        session.flush()

        first = submit_tag_proposal(session, user, " 定向越野 ", "activity", "周末参加定向越野")
        second = submit_tag_proposal(session, user, "定向-越野", "activity", "想找定向越野队友")

        assert first.id == second.id
        assert second.status == "pending"
        assert second.occurrence_count == 2
        assert session.execute(select(TagProposal)).scalars().all() == [second]
        assert session.execute(select(Tag).where(Tag.canonical_name == "定向越野")).scalar_one_or_none() is None


def test_existing_canonical_or_alias_cannot_be_submitted_as_a_new_tag():
    from services.tag_governance import submit_tag_proposal

    with _session() as session:
        seed_content_catalog(session)
        user = _user("student@nju.edu.cn")
        session.add(user)
        session.flush()

        for name in ("羽毛球", "羽球"):
            try:
                submit_tag_proposal(session, user, name, "activity", name)
            except ValueError as exc:
                assert "已有标准标签" in str(exc)
            else:
                raise AssertionError(f"existing concept {name} was accepted as a proposal")


def test_only_operator_can_approve_a_proposal_and_the_decision_is_audited():
    from services.tag_governance import review_tag_proposal, submit_tag_proposal

    with _session() as session:
        seed_content_catalog(session)
        student = _user("student@nju.edu.cn")
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add_all([student, operator])
        session.flush()
        proposal = submit_tag_proposal(session, student, "定向越野", "activity", "活动描述")

        try:
            review_tag_proposal(session, student, proposal, "approve", canonical_name="定向越野")
        except PermissionError as exc:
            assert "运营" in str(exc)
        else:
            raise AssertionError("student unexpectedly reviewed a Tag proposal")

        tag = review_tag_proposal(
            session,
            operator,
            proposal,
            "approve",
            canonical_name="定向越野",
            reason="可复用的校园活动类型",
        )

        assert tag.canonical_name == "定向越野"
        assert tag.active is True
        assert proposal.status == "approved"
        assert proposal.reviewed_by == operator.id
        audit = session.execute(select(AuditLog).where(AuditLog.action == "tag_proposal.approve")).scalar_one()
        assert audit.target_id == str(proposal.id)


def test_operator_can_merge_a_proposal_into_an_existing_tag_alias():
    from services.tag_governance import review_tag_proposal, submit_tag_proposal
    from storage.database.models import TagProposal

    with _session() as session:
        seed_content_catalog(session)
        student = _user("student@nju.edu.cn")
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add_all([student, operator])
        session.flush()
        proposal = submit_tag_proposal(session, student, "羽毛球搭子局", "activity", "找人打球")

        tag = review_tag_proposal(
            session,
            operator,
            proposal,
            "merge",
            target_tag_id="activity_badminton",
            reason="属于羽毛球的表达方式",
        )

        assert tag.id == "activity_badminton"
        assert proposal.status == "merged"
        assert proposal.suggested_tag_id == tag.id
        alias = session.execute(
            select(TagAlias).where(TagAlias.normalized_alias == "羽毛球搭子局")
        ).scalar_one()
        assert alias.tag_id == tag.id
        assert session.execute(select(TagProposal)).scalars().one().id == proposal.id


def test_tag_proposal_routes_submit_list_and_review(monkeypatch):
    from api import content as content_api
    from storage.database.models import TagProposal

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        seed_content_catalog(session)
        student = _user("student@nju.edu.cn")
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add_all([student, operator])
        session.commit()
        student_id = str(student.id)
        operator_id = str(operator.id)
    monkeypatch.setattr(content_api, "get_session", sessions)

    created = content_api.create_tag_proposal(
        {"name": "定向越野", "category": "activity", "source_text": "周末定向越野"},
        student_id,
    )
    proposal_id = int(created["data"]["proposal_id"])
    assert created["data"]["status"] == "pending"

    try:
        content_api.list_tag_proposals("pending", student_id)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("student unexpectedly listed Tag proposals")

    listed = content_api.list_tag_proposals("pending", operator_id)
    assert [item["proposal_id"] for item in listed["data"]] == [str(proposal_id)]

    reviewed = content_api.review_tag_candidate(
        proposal_id,
        {"decision": "approve", "canonical_name": "定向越野", "reason": "常用活动"},
        operator_id,
    )
    assert reviewed["data"]["status"] == "approved"
    with sessions() as session:
        assert session.get(TagProposal, proposal_id).status == "approved"
        assert session.execute(select(Tag).where(Tag.canonical_name == "定向越野")).scalar_one().active is True


def test_ai_candidate_catalog_is_not_truncated_to_the_first_twenty_tags():
    from api.agent import _candidate_tags

    with _session() as session:
        seed_content_catalog(session)

        candidates = _candidate_tags(session)

        assert len(candidates) >= 70
        assert any(item["tag_id"] == "skill_python" for item in candidates)
        assert any(item["tag_id"] == "audience_postgraduate" for item in candidates)


def test_classify_route_stores_sanitized_unknown_concepts_as_pending_proposals(monkeypatch):
    from api import agent
    from storage.database.models import TagProposal

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as session:
        seed_content_catalog(session)
        user = _user("student@nju.edu.cn")
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
                "tag_ids": ["activity_running"],
                "unknown_concepts": [
                    {"name": "定向越野", "category": "activity", "reason": "新的活动类型"},
                    {"name": "x", "category": "activity", "reason": "名称太短"},
                    {"name": "私聊我", "category": "contact", "reason": "非法分类"},
                ],
                "risk_level": "low",
                "suggestions": [],
            },
            ensure_ascii=False,
        ),
    )

    result = agent.classify_review(
        {"title": "定向越野招募", "description": "周末找两名队友"},
        user_id,
    )

    assert result["data"]["tag_ids"] == ["activity_running"]
    assert len(result["data"]["tag_proposals"]) == 1
    assert result["data"]["tag_proposals"][0]["name"] == "定向越野"
    with sessions() as session:
        proposals = session.execute(select(TagProposal)).scalars().all()
        assert [(item.proposed_name, item.status) for item in proposals] == [("定向越野", "pending")]
