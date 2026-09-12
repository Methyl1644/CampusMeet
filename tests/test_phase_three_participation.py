from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable

from storage.database import models as database_models
from storage.database.models import Post, Topic, User
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


@pytest.mark.parametrize(
    ("table_name", "column_name", "invalid_value"),
    [
        ("topics", "participation_mode", "ticketed"),
        ("topics", "capacity", 0),
        ("topics", "capacity", -1),
        ("posts", "purpose", "announcement"),
        ("posts", "join_mode", "invite_only"),
    ],
)
def test_participation_model_checks_reject_invalid_raw_values(
    table_name: str,
    column_name: str,
    invalid_value: str | int,
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
    assert "ck_topics_capacity_positive" in topic_ddl
    assert "capacity IS NULL OR capacity > 0" in topic_ddl
    assert "ck_posts_purpose" in post_ddl
    assert "purpose IN ('team_recruitment', 'official_signup', 'discussion')" in post_ddl
    assert "ck_posts_join_mode" in post_ddl
    assert "join_mode IN ('application', 'direct', 'none')" in post_ddl
    assert "PRIMARY KEY (post_id, user_id)" in bookmark_ddl
    assert "CREATE UNIQUE INDEX uq_posts_effective_official_signup_topic" in official_index_ddl
    assert "purpose = 'official_signup'" in official_index_ddl
    assert "status IN ('recruiting', 'full')" in official_index_ddl
