import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.content import (
    bootstrap_operator,
    build_post_draft,
    create_topic,
    seed_content_catalog,
    suggest_content,
)
from storage.database.models import Organization, OrganizationMember, Tag, Topic, User
from storage.database.shared.model import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(email: str, role: str = "student", verified: bool = True) -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified" if verified else "unverified",
        site_role=role,
    )


def test_tag_alias_maps_to_canonical_tag_without_creating_alias_as_tag():
    with _session() as session:
        seed_content_catalog(session)
        result = suggest_content(session, "羽球", channel="casual")

        assert result["tags"][0]["tag_id"] == "activity_badminton"
        assert result["tags"][0]["canonical_name"] == "羽毛球"
        assert result["tags"][0]["matched_alias"] == "羽球"
        assert session.get(Tag, "羽球") is None


def test_topic_keyword_suggestion_has_priority_over_tag_matches():
    with _session() as session:
        seed_content_catalog(session)
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add(operator)
        session.flush()
        topic = create_topic(
            session,
            operator,
            {
                "channel": "official",
                "title": "美国大学生数学建模竞赛（MCM/ICM）2026",
                "short_title": "美赛 2026",
                "organizer": "COMAP",
                "edition": "2026",
                "summary": "三人团队参加的国际数学建模竞赛",
                "content": "赛事资料",
                "tag_ids": ["activity_math_modeling", "level_international"],
            },
        )
        session.commit()

        result = suggest_content(session, "美赛", channel="official")

        assert result["direct"][0]["entity_type"] == "topic"
        assert result["direct"][0]["entity_id"] == str(topic.id)
        assert "美国大学生数学建模竞赛" in result["direct"][0]["title"]


def test_official_topic_requires_operator_and_duplicate_is_rejected():
    with _session() as session:
        seed_content_catalog(session)
        student = _user("student@nju.edu.cn")
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add_all([student, operator])
        session.flush()
        payload = {
            "channel": "official",
            "title": "挑战杯 2026",
            "short_title": "挑战杯",
            "organizer": "挑战杯组委会",
            "edition": "2026",
            "summary": "大学生课外学术科技作品竞赛",
            "content": "赛事资料",
            "tag_ids": ["activity_innovation"],
        }

        try:
            create_topic(session, student, payload)
        except PermissionError as exc:
            assert "运营" in str(exc)
        else:
            raise AssertionError("student unexpectedly created an official topic")

        create_topic(session, operator, payload)
        session.flush()
        try:
            create_topic(session, operator, payload)
        except ValueError as exc:
            assert "已存在" in str(exc)
        else:
            raise AssertionError("duplicate topic unexpectedly created")


def test_organization_topic_requires_active_publisher_membership():
    with _session() as session:
        seed_content_catalog(session)
        user = _user("publisher@nju.edu.cn")
        org = Organization(name="软件学院学生会", org_type="college", verification_status="approved")
        session.add_all([user, org])
        session.flush()
        session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role="publisher",
                status="active",
                expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30),
            )
        )
        session.flush()

        topic = create_topic(
            session,
            user,
            {
                "channel": "organization",
                "organization_id": org.id,
                "title": "软件学院羽毛球赛",
                "short_title": "软院羽毛球赛",
                "organizer": "软件学院学生会",
                "edition": "2026秋",
                "summary": "面向学院学生的羽毛球活动",
                "content": "活动资料",
                "tag_ids": ["activity_badminton", "level_college"],
            },
        )

        assert topic.organization_id == org.id


def test_post_draft_skip_state_is_terminal_and_tags_are_whitelisted():
    candidates = [
        {"tag_id": "activity_badminton", "canonical_name": "羽毛球"},
        {"tag_id": "activity_basketball", "canonical_name": "篮球"},
    ]
    first = build_post_draft(
        kind="casual_invitation",
        message="周五在仙林打羽球",
        previous_fields={},
        candidates=candidates,
    )
    assert first["suggested_tag_ids"] == ["activity_badminton"]

    second = build_post_draft(
        kind="casual_invitation",
        message="不知道",
        previous_fields=first["field_states"],
        candidates=candidates,
    )
    terminal = [key for key, state in second["field_states"].items() if state["status"] == "unknown"]
    assert len(terminal) == 1
    assert second["next_field"] != terminal[0]
    assert set(second["suggested_tag_ids"]).issubset({"activity_badminton", "activity_basketball"})


def test_casual_draft_uses_fields_the_frontend_can_publish():
    draft = build_post_draft(
        kind="casual_invitation",
        message="羽毛球",
        previous_fields={},
        candidates=[],
    )

    assert tuple(draft["field_states"]) == (
        "activity_name",
        "target_members",
        "weekly_hours",
        "school_scope",
        "needed_roles",
        "description",
    )


def test_casual_draft_extracts_explicit_details_and_asks_one_specific_question():
    message = "我现在想要在这周六的下午，约两个羽毛球的搭子，场地已经约好，男女不限，对技术也无要求"
    candidates = [
        {
            "tag_id": "activity_badminton",
            "canonical_name": "羽毛球",
            "category": "activity",
        }
    ]

    result = build_post_draft(
        kind="casual_invitation",
        message=message,
        previous_fields={},
        candidates=candidates,
    )

    assert result["draft"]["activity_name"] == "羽毛球"
    assert result["draft"]["target_members"] == 3
    assert result["draft"]["weekly_hours"] == "这周六下午"
    assert result["draft"]["needed_roles"] == []
    assert result["field_states"]["needed_roles"]["status"] == "none"
    assert result["field_states"]["school_scope"]["status"] == "pending"
    assert result["next_field"] == "school_scope"
    assert result["missing_fields"] == ["school_scope"]
    assert "地点" in result["reply"]
    assert result["reply"] != "信息已整理，请继续补充。"
    assert all(
        state["value"] != message
        for state in result["field_states"].values()
    )


def test_casual_draft_routes_each_follow_up_to_its_meaningful_field():
    candidates = [
        {
            "tag_id": "activity_badminton",
            "canonical_name": "羽毛球",
            "category": "activity",
        }
    ]
    first = build_post_draft(
        kind="casual_invitation",
        message="找两个羽毛球搭子",
        previous_fields={},
        candidates=candidates,
    )
    second = build_post_draft(
        kind="casual_invitation",
        message="周末下午",
        previous_fields=first["field_states"],
        candidates=candidates,
    )
    third = build_post_draft(
        kind="casual_invitation",
        message="仙林体育馆",
        previous_fields=second["field_states"],
        candidates=candidates,
    )
    fourth = build_post_draft(
        kind="casual_invitation",
        message="水平不限，男女不限",
        previous_fields=third["field_states"],
        candidates=candidates,
    )

    assert first["draft"]["activity_name"] == "羽毛球"
    assert first["draft"]["target_members"] == 3
    assert first["next_field"] == "weekly_hours"
    assert second["draft"]["weekly_hours"] == "周末下午"
    assert second["next_field"] == "school_scope"
    assert third["draft"]["school_scope"] == "仙林体育馆"
    assert third["next_field"] == "needed_roles"
    assert fourth["draft"]["needed_roles"] == []
    assert fourth["is_complete"] is True
    assert fourth["missing_fields"] == []


def test_casual_draft_treats_explicit_total_people_as_including_the_author():
    result = build_post_draft(
        kind="casual_invitation",
        message="想约羽毛球，总共三人",
        previous_fields={},
        candidates=[
            {
                "tag_id": "activity_badminton",
                "canonical_name": "羽毛球",
                "category": "activity",
            }
        ],
    )

    assert result["draft"]["target_members"] == 3


def test_casual_draft_keeps_known_event_name_separate_from_standard_tags():
    result = build_post_draft(
        kind="casual_invitation",
        message="找个美赛队友",
        previous_fields={},
        candidates=[
            {
                "tag_id": "activity_math_modeling",
                "canonical_name": "数学建模",
                "category": "activity",
            }
        ],
    )

    assert result["draft"]["activity_name"] == "美赛"
    assert result["draft"]["target_members"] == 2
    assert result["suggested_tag_ids"] == ["activity_math_modeling"]
    assert result["next_field"] == "weekly_hours"


def test_casual_draft_accepts_a_bare_number_when_answering_the_people_question():
    previous_fields = {
        "activity_name": {"value": "羽毛球", "status": "confirmed"},
        "target_members": {"value": None, "status": "pending"},
        "weekly_hours": {"value": None, "status": "pending"},
        "school_scope": {"value": None, "status": "pending"},
        "needed_roles": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="casual_invitation",
        message="3",
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["target_members"] == 3
    assert result["next_field"] == "weekly_hours"


def test_topic_draft_accepts_a_date_when_answering_the_deadline_question():
    previous_fields = {
        "activity_name": {"value": "美赛", "status": "confirmed"},
        "target_members": {"value": 3, "status": "confirmed"},
        "needed_roles": {"value": ["编程"], "status": "confirmed"},
        "weekly_hours": {"value": "每周10小时", "status": "confirmed"},
        "school_scope": {"value": "仙林校区", "status": "confirmed"},
        "deadline": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="topic_team",
        message="9月20日",
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["deadline"] == "9月20日"
    assert result["is_complete"] is True


def test_follow_up_location_does_not_overwrite_a_confirmed_activity():
    previous_fields = {
        "activity_name": {"value": "羽毛球", "status": "confirmed"},
        "target_members": {"value": 3, "status": "confirmed"},
        "weekly_hours": {"value": "周末下午", "status": "confirmed"},
        "school_scope": {"value": None, "status": "pending"},
        "needed_roles": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="casual_invitation",
        message="篮球场",
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["activity_name"] == "羽毛球"
    assert result["draft"]["school_scope"] == "篮球场"
    assert result["next_field"] == "needed_roles"


@pytest.mark.parametrize("message", ["地点改为篮球场", "活动地点改为篮球场"])
def test_location_correction_only_updates_the_location_field(message):
    previous_fields = {
        "activity_name": {"value": "羽毛球", "status": "confirmed"},
        "target_members": {"value": 3, "status": "confirmed"},
        "weekly_hours": {"value": "周末下午", "status": "confirmed"},
        "school_scope": {"value": "仙林体育馆", "status": "confirmed"},
        "needed_roles": {"value": None, "status": "none"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="casual_invitation",
        message=message,
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["activity_name"] == "羽毛球"
    assert result["draft"]["school_scope"] == "篮球场"


def test_unlimited_scope_and_unlimited_skill_update_different_fields():
    previous_fields = {
        "activity_name": {"value": "羽毛球", "status": "confirmed"},
        "target_members": {"value": 3, "status": "confirmed"},
        "weekly_hours": {"value": "周末下午", "status": "confirmed"},
        "school_scope": {"value": None, "status": "pending"},
        "needed_roles": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    scope_result = build_post_draft(
        kind="casual_invitation",
        message="校区不限",
        previous_fields=previous_fields,
        candidates=[],
    )
    role_result = build_post_draft(
        kind="casual_invitation",
        message="技术不限",
        previous_fields=scope_result["field_states"],
        candidates=[],
    )

    assert scope_result["field_states"]["school_scope"]["status"] == "none"
    assert scope_result["field_states"]["needed_roles"]["status"] == "pending"
    assert role_result["field_states"]["needed_roles"]["status"] == "none"
    assert role_result["is_complete"] is True


@pytest.mark.parametrize("message", ["Python 不限", "不需要会 Python"])
def test_negated_skill_is_not_treated_as_a_positive_requirement(message):
    previous_fields = {
        "activity_name": {"value": "数学建模", "status": "confirmed"},
        "target_members": {"value": 3, "status": "confirmed"},
        "weekly_hours": {"value": "每周10小时", "status": "confirmed"},
        "school_scope": {"value": "仙林校区", "status": "confirmed"},
        "needed_roles": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="casual_invitation",
        message=message,
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["needed_roles"] == []
    assert result["field_states"]["needed_roles"]["status"] == "none"
    assert result["is_complete"] is True


def test_casual_draft_accepts_a_short_free_form_location_answer():
    previous_fields = {
        "activity_name": {"value": "自习", "status": "confirmed"},
        "target_members": {"value": 2, "status": "confirmed"},
        "weekly_hours": {"value": "周末下午", "status": "confirmed"},
        "school_scope": {"value": None, "status": "pending"},
        "needed_roles": {"value": None, "status": "pending"},
        "description": {"value": None, "status": "none"},
    }

    result = build_post_draft(
        kind="casual_invitation",
        message="费彝民楼A201",
        previous_fields=previous_fields,
        candidates=[],
    )

    assert result["draft"]["school_scope"] == "费彝民楼A201"
    assert result["next_field"] == "needed_roles"


def test_topic_suggestions_search_all_active_topics_not_only_latest_100():
    with _session() as session:
        operator = _user("operator@nju.edu.cn", role="operator")
        session.add(operator)
        session.flush()
        for index in range(101):
            session.add(
                Topic(
                    channel="official",
                    title=f"普通活动 {index}",
                    short_title=f"活动 {index}",
                    organizer="平台",
                    organizer_key="平台",
                    canonical_event_key=f"event{index}",
                    edition="2026",
                    summary="简介",
                    content="资料",
                    created_by=operator.id,
                )
            )
        session.add(
            Topic(
                channel="official",
                title="历史全国大学生羽毛球挑战赛",
                short_title="历史羽球赛",
                organizer="平台",
                organizer_key="平台",
                canonical_event_key="historybadminton",
                edition="2025",
                summary="简介",
                content="资料",
                created_by=operator.id,
                updated_at=datetime.datetime(2020, 1, 1),
            )
        )
        session.commit()

        result = suggest_content(session, "历史羽球赛", channel="official")

        assert result["direct"][0]["title"] == "历史全国大学生羽毛球挑战赛"


def test_bootstrap_operator_promotes_only_the_configured_existing_account():
    with _session() as session:
        target = _user("owner@nju.edu.cn")
        other = _user("other@nju.edu.cn")
        session.add_all([target, other])
        session.commit()

        assert bootstrap_operator(session, "owner@nju.edu.cn") is True
        session.commit()

        assert target.site_role == "senior_operator"
        assert other.site_role == "student"
        assert bootstrap_operator(session, "missing@nju.edu.cn") is False
