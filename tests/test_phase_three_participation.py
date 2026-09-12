from __future__ import annotations

import importlib
import json

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateIndex, CreateTable

from storage.database import models as database_models
from storage.database.models import Application, Conversation, Post, Team, TeamMember, Topic, User
from storage.database.shared.model import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _user(email: str) -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
    )


def _topic(user_id: int, **overrides) -> Topic:
    values = {
        "channel": "official",
        "title": "Campus activity",
        "short_title": "Activity",
        "organizer": "CampusMate",
        "organizer_key": "campusmate",
        "canonical_event_key": "campus-activity",
        "edition": "2026",
        "summary": "Summary",
        "content": "Details",
        "created_by": user_id,
    }
    values.update(overrides)
    return Topic(**values)


def _post(user_id: int, topic_id: int | None = None, **overrides) -> Post:
    values = {
        "title": "Find teammates",
        "topic_id": topic_id,
        "main_category": "sports",
        "activity_name": "Badminton",
        "target_members": 4,
        "author_id": user_id,
    }
    values.update(overrides)
    return Post(**values)


def _post_bookmark_model():
    model = getattr(database_models, "PostBookmark", None)
    assert model is not None, "PostBookmark must be exported from database models"
    return model


def _participation_service():
    return importlib.import_module("services.participation")


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_participation_models_persist_safe_legacy_defaults():
    with _session() as session:
        user = _user("defaults@nju.edu.cn")
        session.add(user)
        session.flush()
        topic = _topic(user.id)
        session.add(topic)
        session.flush()
        post = _post(user.id, topic.id)
        session.add(post)
        session.flush()

        assert topic.location_name is None
        assert topic.campus_scope is None
        assert topic.capacity is None
        assert topic.participation_mode == "open_team"
        assert post.cover_url is None
        assert post.purpose == "team_recruitment"
        assert post.join_mode == "application"


def test_participation_database_defaults_apply_to_raw_sqlite_inserts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = _user("raw-defaults@nju.edu.cn")
        session.add(user)
        session.commit()
        user_id = user.id

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO topics ("
                "id, channel, title, short_title, organizer, organizer_key, "
                "canonical_event_key, edition, summary, content, source_status, "
                "created_by, status) VALUES ("
                "100, 'official', 'Raw activity', 'Raw', 'CampusMate', 'campusmate', "
                "'raw-activity', '2026', 'Summary', 'Details', 'verified', :user_id, 'active')"
            ),
            {"user_id": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO posts ("
                "id, title, source_type, kind, topic_id, main_category, activity_name, "
                "tags, current_members, target_members, needed_roles, risk_level, status, author_id) VALUES ("
                "200, 'Raw group', 'user', 'casual_invitation', 100, 'sports', "
                "'Badminton', '[]', 1, 4, '[]', 'low', 'recruiting', :user_id)"
            ),
            {"user_id": user_id},
        )
        topic_defaults = connection.execute(
            text("SELECT participation_mode FROM topics WHERE id = 100")
        ).one()
        post_defaults = connection.execute(
            text("SELECT purpose, join_mode FROM posts WHERE id = 200")
        ).one()

    assert tuple(topic_defaults) == ("open_team",)
    assert tuple(post_defaults) == ("team_recruitment", "application")


@pytest.mark.parametrize(
    ("table_name", "column_name", "invalid_value"),
    [
        ("topics", "participation_mode", "ticketed"),
        ("topics", "capacity", 0),
        ("topics", "capacity", -1),
        ("topics", "capacity", 1.5),
        ("topics", "capacity", "abc"),
        ("posts", "purpose", "announcement"),
        ("posts", "join_mode", "invite_only"),
    ],
)
def test_participation_model_checks_reject_invalid_raw_values(
    table_name: str,
    column_name: str,
    invalid_value: str | int | float,
):
    with _session() as session:
        user = _user(f"{table_name}-{column_name}-{invalid_value}@nju.edu.cn")
        session.add(user)
        session.flush()
        topic = _topic(user.id)
        session.add(topic)
        session.flush()
        post = _post(user.id, topic.id)
        session.add(post)
        session.commit()
        row_id = topic.id if table_name == "topics" else post.id

        with pytest.raises(IntegrityError):
            session.execute(
                text(f"UPDATE {table_name} SET {column_name} = :value WHERE id = :id"),
                {"value": invalid_value, "id": row_id},
            )
            session.commit()


def test_effective_official_signup_is_unique_per_topic():
    with _session() as session:
        user = _user("official-signup@nju.edu.cn")
        session.add(user)
        session.flush()
        topic = _topic(user.id)
        session.add(topic)
        session.flush()
        session.add(
            _post(
                user.id,
                topic.id,
                title="Official signup",
                purpose="official_signup",
                join_mode="direct",
                status="recruiting",
            )
        )
        session.commit()

        session.add(
            _post(
                user.id,
                topic.id,
                title="Duplicate official signup",
                purpose="official_signup",
                join_mode="direct",
                status="full",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            _post(
                user.id,
                topic.id,
                title="Closed historical signup",
                purpose="official_signup",
                join_mode="direct",
                status="closed",
            )
        )
        session.commit()


def test_post_bookmark_is_unique_and_has_user_created_index():
    PostBookmark = _post_bookmark_model()
    with _session() as session:
        user = _user("bookmark@nju.edu.cn")
        session.add(user)
        session.flush()
        post = _post(user.id)
        session.add(post)
        session.flush()
        session.add(PostBookmark(post_id=post.id, user_id=user.id))
        session.commit()

        session.add(PostBookmark(post_id=post.id, user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()

        indexes = {
            item["name"]: item
            for item in inspect(session.get_bind()).get_indexes("post_bookmarks")
        }
        assert indexes["ix_post_bookmarks_user_created"]["column_names"] == [
            "user_id",
            "created_at",
            "post_id",
        ]


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect()])
def test_participation_model_metadata_emits_dialect_safe_ddl(dialect):
    PostBookmark = _post_bookmark_model()
    topic_ddl = str(CreateTable(Topic.__table__).compile(dialect=dialect))
    post_ddl = str(CreateTable(Post.__table__).compile(dialect=dialect))
    bookmark_ddl = str(CreateTable(PostBookmark.__table__).compile(dialect=dialect))
    official_index = next(
        index
        for index in Post.__table__.indexes
        if index.name == "uq_posts_effective_official_signup_topic"
    )
    official_index_ddl = str(CreateIndex(official_index).compile(dialect=dialect))

    assert "ck_topics_participation_mode" in topic_ddl
    assert "participation_mode IN ('open_team', 'official_signup', 'information_only')" in topic_ddl
    assert "participation_mode TEXT DEFAULT 'open_team' NOT NULL" in topic_ddl
    assert "ck_topics_capacity_positive" in topic_ddl
    if dialect.name == "sqlite":
        assert "capacity IS NULL OR (typeof(capacity) = 'integer' AND capacity > 0)" in topic_ddl
        assert "typeof(capacity) = 'integer'" in topic_ddl
    else:
        assert "capacity IS NULL OR capacity > 0" in topic_ddl
        assert "typeof" not in topic_ddl
    assert "ck_posts_purpose" in post_ddl
    assert "purpose IN ('team_recruitment', 'official_signup', 'discussion')" in post_ddl
    assert "purpose TEXT DEFAULT 'team_recruitment' NOT NULL" in post_ddl
    assert "ck_posts_join_mode" in post_ddl
    assert "join_mode IN ('application', 'direct', 'none')" in post_ddl
    assert "join_mode TEXT DEFAULT 'application' NOT NULL" in post_ddl
    assert "PRIMARY KEY (post_id, user_id)" in bookmark_ddl
    assert "CREATE UNIQUE INDEX uq_posts_effective_official_signup_topic" in official_index_ddl
    assert "purpose = 'official_signup'" in official_index_ddl
    assert "status IN ('recruiting', 'full')" in official_index_ddl


@pytest.mark.parametrize(
    ("participation_mode", "purpose", "expected_join_mode", "expected_error"),
    [
        ("open_team", "team_recruitment", "application", None),
        ("open_team", "official_signup", None, "participation.forbidden_purpose"),
        ("open_team", "discussion", "none", None),
        ("official_signup", "team_recruitment", None, "participation.forbidden_purpose"),
        ("official_signup", "official_signup", "direct", None),
        ("official_signup", "discussion", "none", None),
        ("information_only", "team_recruitment", None, "participation.forbidden_purpose"),
        ("information_only", "official_signup", None, "participation.forbidden_purpose"),
        ("information_only", "discussion", "none", None),
    ],
)
def test_participation_policy_covers_every_mode_and_purpose_combination(
    participation_mode: str,
    purpose: str,
    expected_join_mode: str | None,
    expected_error: str | None,
):
    participation = _participation_service()
    with _session() as session:
        organizer = _user(f"{participation_mode}-{purpose}@nju.edu.cn")
        if participation_mode == "official_signup" and purpose == "official_signup":
            organizer.site_role = "operator"
        session.add(organizer)
        session.flush()
        topic = _topic(organizer.id, participation_mode=participation_mode)
        session.add(topic)
        session.flush()

        if expected_error:
            with pytest.raises(participation.ParticipationError) as caught:
                participation.validate_post_participation(
                    session,
                    organizer,
                    {"topic_id": topic.id, "purpose": purpose},
                )
            assert caught.value.code == expected_error
            return

        decision = participation.validate_post_participation(
            session,
            organizer,
            {"topic_id": topic.id, "purpose": purpose},
        )
        assert decision.participation_mode == participation_mode
        assert decision.purpose == purpose
        assert decision.join_mode == expected_join_mode


def test_only_activity_managers_can_create_official_signup_posts():
    participation = _participation_service()
    with _session() as session:
        organizer = _user("official-organizer@nju.edu.cn")
        organizer.site_role = "operator"
        outsider = _user("official-outsider@nju.edu.cn")
        session.add_all([organizer, outsider])
        session.flush()
        topic = _topic(organizer.id, participation_mode="official_signup")
        session.add(topic)
        session.flush()

        with pytest.raises(participation.ParticipationError) as caught:
            participation.validate_post_participation(
                session,
                outsider,
                {"topic_id": topic.id, "purpose": "official_signup"},
            )

        assert caught.value.code == "participation.official_signup_forbidden"
        assert caught.value.message == "只有活动管理者可以发布官方报名帖"


def test_official_signup_uniqueness_ignores_the_updated_post_and_closed_history():
    participation = _participation_service()
    with _session() as session:
        organizer = _user("official-unique@nju.edu.cn")
        organizer.site_role = "operator"
        session.add(organizer)
        session.flush()
        topic = _topic(organizer.id, participation_mode="official_signup")
        session.add(topic)
        session.flush()
        official = _post(
            organizer.id,
            topic.id,
            purpose="official_signup",
            join_mode="direct",
            status="recruiting",
        )
        session.add(official)
        session.commit()

        unchanged = participation.validate_post_participation(
            session,
            organizer,
            {},
            existing=official,
        )
        assert unchanged.purpose == "official_signup"

        with pytest.raises(participation.ParticipationError) as caught:
            participation.validate_post_participation(
                session,
                organizer,
                {"topic_id": topic.id, "purpose": "official_signup"},
            )
        assert caught.value.code == "participation.duplicate_official_signup"
        assert caught.value.message == "该活动已有有效的官方报名帖"

        official.status = "closed"
        session.flush()
        replacement = participation.validate_post_participation(
            session,
            organizer,
            {"topic_id": topic.id, "purpose": "official_signup"},
        )
        assert replacement.join_mode == "direct"


def test_policy_rejects_noncanonical_join_modes_with_stable_error():
    participation = _participation_service()
    with _session() as session:
        organizer = _user("invalid-join-mode@nju.edu.cn")
        session.add(organizer)
        session.flush()
        topic = _topic(organizer.id, participation_mode="open_team")
        session.add(topic)
        session.flush()

        with pytest.raises(participation.ParticipationError) as caught:
            participation.validate_post_participation(
                session,
                organizer,
                {
                    "topic_id": topic.id,
                    "purpose": "team_recruitment",
                    "join_mode": "direct",
                },
            )

        assert caught.value.code == "participation.invalid_join_mode"
        assert caught.value.message == "帖子加入方式与用途不匹配"


def test_direct_join_creates_one_team_and_is_idempotent():
    participation = _participation_service()
    with _session() as session:
        organizer = _user("direct-owner@nju.edu.cn")
        attendee = _user("direct-attendee@nju.edu.cn")
        session.add_all([organizer, attendee])
        session.flush()
        topic = _topic(organizer.id, participation_mode="official_signup", capacity=3)
        session.add(topic)
        session.flush()
        post = _post(
            organizer.id,
            topic.id,
            purpose="official_signup",
            join_mode="direct",
            target_members=100,
        )
        session.add(post)
        session.flush()

        first = participation.join_post_directly(session, post, attendee)
        second = participation.join_post_directly(session, post, attendee)
        session.flush()

        assert first.id == second.id
        assert session.query(Team).count() == 1
        assert session.query(TeamMember).count() == 2
        assert post.current_members == 2
        assert attendee.team_count == 1
        assert participation.get_join_state(session, post, organizer.id) == "owner"
        assert participation.get_join_state(session, post, attendee.id) == "joined"


def test_direct_join_checks_topic_capacity_and_preserves_repeat_success():
    participation = _participation_service()
    with _session() as session:
        organizer = _user("capacity-owner@nju.edu.cn")
        first_attendee = _user("capacity-first@nju.edu.cn")
        blocked_attendee = _user("capacity-blocked@nju.edu.cn")
        session.add_all([organizer, first_attendee, blocked_attendee])
        session.flush()
        topic = _topic(organizer.id, participation_mode="official_signup", capacity=2)
        session.add(topic)
        session.flush()
        post = _post(
            organizer.id,
            topic.id,
            purpose="official_signup",
            join_mode="direct",
            target_members=100,
        )
        session.add(post)
        session.flush()

        membership = participation.join_post_directly(session, post, first_attendee)
        assert post.status == "full"
        assert participation.join_post_directly(session, post, first_attendee).id == membership.id

        with pytest.raises(participation.ParticipationError) as caught:
            participation.join_post_directly(session, post, blocked_attendee)
        assert caught.value.code == "participation.full"
        assert caught.value.message == "活动名额已满"


def test_direct_join_rejects_a_noncanonical_purpose_before_team_creation():
    participation = _participation_service()
    with _session() as session:
        owner = _user("direct-invalid-owner@nju.edu.cn")
        attendee = _user("direct-invalid-attendee@nju.edu.cn")
        session.add_all([owner, attendee])
        session.flush()
        post = _post(owner.id, purpose="discussion", join_mode="direct")
        session.add(post)
        session.flush()

        with pytest.raises(participation.ParticipationError) as caught:
            participation.join_post_directly(session, post, attendee)

        assert caught.value.code == "participation.invalid_join_mode"
        assert session.query(Team).count() == 0


def test_get_join_state_covers_pending_rejected_available_and_closed():
    participation = _participation_service()
    with _session() as session:
        owner = _user("states-owner@nju.edu.cn")
        pending_user = _user("states-pending@nju.edu.cn")
        rejected_user = _user("states-rejected@nju.edu.cn")
        available_user = _user("states-available@nju.edu.cn")
        session.add_all([owner, pending_user, rejected_user, available_user])
        session.flush()
        post = _post(owner.id, join_mode="application")
        session.add(post)
        session.flush()
        session.add_all(
            [
                Application(
                    post_id=post.id,
                    applicant_id=pending_user.id,
                    role_wanted="member",
                    experience="experience",
                    available_time="weekend",
                    reason="join",
                    status="pending",
                ),
                Application(
                    post_id=post.id,
                    applicant_id=rejected_user.id,
                    role_wanted="member",
                    experience="experience",
                    available_time="weekend",
                    reason="join",
                    status="rejected",
                ),
            ]
        )
        session.flush()

        assert participation.get_join_state(session, post, pending_user.id) == "pending"
        assert participation.get_join_state(session, post, rejected_user.id) == "rejected"
        assert participation.get_join_state(session, post, available_user.id) == "available"
        post.status = "closed"
        assert participation.get_join_state(session, post, available_user.id) == "closed"


def test_application_join_rejects_direct_and_information_only_posts():
    participation = _participation_service()
    with _session() as session:
        owner = _user("application-owner@nju.edu.cn")
        applicant = _user("application-user@nju.edu.cn")
        session.add_all([owner, applicant])
        session.flush()
        topic = _topic(owner.id, participation_mode="official_signup")
        session.add(topic)
        session.flush()
        direct_post = _post(
            owner.id,
            topic.id,
            purpose="official_signup",
            join_mode="direct",
        )
        session.add(direct_post)
        session.flush()

        with pytest.raises(participation.ParticipationError) as caught:
            participation.validate_application_join(session, direct_post, applicant)
        assert caught.value.code == "participation.invalid_join_mode"

        topic.participation_mode = "information_only"
        direct_post.purpose = "discussion"
        direct_post.join_mode = "none"
        with pytest.raises(participation.ParticipationError) as caught:
            participation.validate_application_join(session, direct_post, applicant)
        assert caught.value.code == "participation.invalid_join_mode"


def test_post_create_and_update_paths_apply_the_policy(monkeypatch):
    from api import posts as posts_api
    from api.schemas.collaboration import PostCreateRequest
    from tools import post_tools

    factory = _factory()
    with factory() as session:
        operator = _user("post-policy-owner@nju.edu.cn")
        operator.auth_status = "verified"
        operator.site_role = "operator"
        session.add(operator)
        session.flush()
        topic = _topic(operator.id, participation_mode="official_signup")
        session.add(topic)
        session.commit()
        operator_id = operator.id
        topic_id = topic.id

    monkeypatch.setattr(post_tools, "get_session", factory)
    monkeypatch.setattr(posts_api, "get_session", factory)
    monkeypatch.setattr(posts_api, "_moderate_post", lambda *args, **kwargs: None)
    monkeypatch.setattr(posts_api, "_classification_review", lambda *args, **kwargs: {})

    created = posts_api.create(
        PostCreateRequest(
            title="Official signup",
            description="Campus registration",
            main_category="校园生活",
            activity_name="Campus activity",
            target_members=20,
            needed_roles=[],
            kind="topic_team",
            topic_id=topic_id,
            purpose="official_signup",
            join_mode="direct",
        ),
        str(operator_id),
    )
    post_id = int(created["data"]["id"])
    assert created["data"]["cover_url"] is None
    assert created["data"]["purpose"] == "official_signup"
    assert created["data"]["join_mode"] == "direct"

    updated = posts_api.update(
        post_id,
        {"title": "Official signup updated", "purpose": "discussion", "join_mode": "none"},
        str(operator_id),
    )
    assert updated["data"]["title"] == "Official signup updated"
    assert updated["data"]["purpose"] == "discussion"
    assert updated["data"]["join_mode"] == "none"
    with factory() as session:
        stored = session.get(Post, post_id)
        assert stored.purpose == "discussion"
        assert stored.join_mode == "none"


def test_post_tool_keeps_policy_inputs_and_adds_task_three_public_projection():
    from tools import post_tools

    assert "purpose" in post_tools.create_post.args
    assert "join_mode" in post_tools.create_post.args
    assert "cover_url" not in post_tools.create_post.args

    post = _post(
        1,
        purpose="official_signup",
        join_mode="direct",
        cover_url="https://example.test/cover.jpg",
    )
    projection = post_tools._post_to_dict(post)
    assert projection["cover_url"] == "https://example.test/cover.jpg"
    assert projection["purpose"] == "official_signup"
    assert projection["join_mode"] == "direct"


def test_application_tool_routes_join_mode_errors_through_policy(monkeypatch):
    from tools import application_tools

    factory = _factory()
    with factory() as session:
        owner = _user("application-route-owner@nju.edu.cn")
        owner.auth_status = "verified"
        applicant = _user("application-route-user@nju.edu.cn")
        applicant.auth_status = "verified"
        session.add_all([owner, applicant])
        session.flush()
        topic = _topic(owner.id, participation_mode="official_signup")
        session.add(topic)
        session.flush()
        post = _post(
            owner.id,
            topic.id,
            purpose="official_signup",
            join_mode="direct",
        )
        session.add(post)
        session.commit()
        applicant_id = applicant.id
        post_id = post.id

    monkeypatch.setattr(application_tools, "get_session", factory)
    result = json.loads(
        application_tools.create_application.invoke(
            {
                "user_id": str(applicant_id),
                "post_id": str(post_id),
                "role_wanted": "attendee",
                "experience": "interested",
                "available_time": "weekend",
                "reason": "join",
                "questions": "",
            }
        )
    )

    assert result["success"] is False
    assert result["error_code"] == "participation.invalid_join_mode"
    assert result["message"] == "帖子加入方式与用途不匹配"
    with factory() as session:
        assert session.query(Application).count() == 0


def test_team_confirmation_rechecks_capacity_through_participation_policy(monkeypatch):
    from tools import message_tools

    factory = _factory()
    with factory() as session:
        owner = _user("confirmation-owner@nju.edu.cn")
        owner.auth_status = "verified"
        applicant = _user("confirmation-applicant@nju.edu.cn")
        applicant.auth_status = "verified"
        existing_member = _user("confirmation-member@nju.edu.cn")
        existing_member.auth_status = "verified"
        session.add_all([owner, applicant, existing_member])
        session.flush()
        post = _post(
            owner.id,
            current_members=2,
            target_members=2,
            purpose="team_recruitment",
            join_mode="application",
            status="full",
        )
        session.add(post)
        session.flush()
        application = Application(
            post_id=post.id,
            applicant_id=applicant.id,
            role_wanted="member",
            experience="experience",
            available_time="weekend",
            reason="join",
            status="accepted",
        )
        session.add(application)
        session.flush()
        conversation = Conversation(
            post_id=post.id,
            post_author_id=owner.id,
            applicant_id=applicant.id,
            application_id=application.id,
            status="active",
            author_confirmed=True,
        )
        team = Team(post_id=post.id, owner_id=owner.id, activity_name=post.activity_name)
        session.add_all([conversation, team])
        session.flush()
        session.add_all(
            [
                TeamMember(team_id=team.id, user_id=owner.id, member_role="owner"),
                TeamMember(team_id=team.id, user_id=existing_member.id, member_role="member"),
            ]
        )
        session.commit()
        conversation_id = conversation.id
        applicant_id = applicant.id
        team_id = team.id

    monkeypatch.setattr(message_tools, "get_session", factory)
    result = json.loads(
        message_tools.confirm_team.invoke(
            {"user_id": str(applicant_id), "conversation_id": str(conversation_id)}
        )
    )

    assert result["success"] is False
    assert result["error_code"] == "participation.full"
    with factory() as session:
        assert session.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == applicant_id,
            )
        ) is None
