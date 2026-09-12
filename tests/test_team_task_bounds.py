from __future__ import annotations

import json
import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.schema import CreateTable
from sqlalchemy.orm import sessionmaker

from storage.database.models import Post, Team, User
from storage.database.models.team import (
    POSTGRESQL_TEAM_TASK_CHECK,
    TEAM_TASK_FIELD_LIMITS,
    TEAM_TASK_JSON_MAX_BYTES,
    normalize_team_task_list,
)
from storage.database.shared.model import Base


def _serialized_bytes(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=True).encode("utf-8"))


def test_team_task_normalizer_rejects_non_arrays_and_bounds_shape_and_bytes():
    assert normalize_team_task_list({"id": "not-an-array"}) == []
    assert normalize_team_task_list("not-an-array") == []

    huge = "任务" * 10_000
    tasks = [
        {
            "id": huge,
            "title": huge,
            "assignee_id": huge,
            "assignee_name": huge,
            "due_at": huge,
            "deadline": huge,
            "done": index % 2 == 0,
            "created_by": huge,
        }
        for index in range(40)
    ]
    normalized = normalize_team_task_list(tasks)

    assert 0 < len(normalized) <= 12
    assert _serialized_bytes(normalized) <= TEAM_TASK_JSON_MAX_BYTES
    assert all(set(task) <= set(TEAM_TASK_FIELD_LIMITS) | {"done"} for task in normalized)
    assert all(isinstance(task["id"], str) for task in normalized)
    assert all(isinstance(task["title"], str) for task in normalized)
    assert all(isinstance(task["done"], bool) for task in normalized)
    for task in normalized:
        for field, (max_chars, max_bytes) in TEAM_TASK_FIELD_LIMITS.items():
            if field in task:
                assert len(task[field]) <= max_chars
                assert len(task[field].encode("utf-8")) <= max_bytes


def test_team_task_normalizer_discards_invalid_items_and_types():
    assert normalize_team_task_list(
        [
            None,
            "task",
            {"id": 7, "title": "wrong id"},
            {"id": "missing-title", "done": False},
            {
                "id": "valid",
                "title": "  Valid task  ",
                "assignee_id": 9,
                "assignee_name": "  Owner  ",
                "due_at": None,
                "deadline": "  2026-09-20  ",
                "done": "yes",
            },
        ]
    ) == [
        {
            "id": "valid",
            "title": "Valid task",
            "assignee_name": "Owner",
            "deadline": "2026-09-20",
            "done": False,
        }
    ]


def test_team_task_normalizer_sanitizes_malformed_unicode_and_preserves_supplementary_text():
    malformed = "prefix\ud800\x00\x01🚀suffix\udfff"

    normalized = normalize_team_task_list(
        [{"id": f"id-{malformed}", "title": malformed, "done": False}]
    )

    assert len(normalized) == 1
    for value in (normalized[0]["id"], normalized[0]["title"]):
        assert "🚀" in value
        assert "\x00" not in value
        assert "\x01" not in value
        assert not any(0xD800 <= ord(character) <= 0xDFFF for character in value)
        value.encode("utf-8", errors="strict")
    json.dumps(normalized, ensure_ascii=False).encode("utf-8", errors="strict")


@pytest.mark.parametrize("input_size", [13, 250])
def test_team_model_bounds_task_json_before_and_after_persistence(input_size):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tasks = [
        {"id": f"task-{index}", "title": f"任务 {index}", "done": False}
        for index in range(input_size)
    ]

    with factory() as session:
        session.add(
            User(
                id=1,
                email="owner@nju.edu.cn",
                password_hash="hash",
                nickname="owner",
                auth_status="verified",
            )
        )
        session.add(
            Post(
                id=1,
                title="增长测试小组",
                main_category="竞赛与项目",
                activity_name="增长测试小组",
                target_members=4,
                author_id=1,
            )
        )
        team = Team(
            id=1,
            post_id=1,
            owner_id=1,
            activity_name="增长测试小组",
            task_list=tasks,
        )

        assert len(team.task_list) == 12
        assert [task["id"] for task in team.task_list] == [
            f"task-{index}" for index in range(12)
        ]

        session.add(team)
        session.commit()
        session.expire(team, ["task_list"])

        persisted = session.scalar(select(Team.task_list).where(Team.id == team.id))
        assert len(persisted) == 12
        assert [task["id"] for task in persisted] == [
            f"task-{index}" for index in range(12)
        ]


def test_team_model_sqlite_checks_reject_wrong_shape_and_oversized_json():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    oversized = json.dumps(
        [{"id": "huge", "title": "x" * TEAM_TASK_JSON_MAX_BYTES, "done": False}]
    )

    for task_list in (json.dumps({"id": "object"}), oversized):
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO teams (id, post_id, activity_name, task_list) "
                        "VALUES (100, 100, 'raw', :task_list)"
                    ),
                    {"task_list": task_list},
                )


def test_team_model_emits_equivalent_sqlite_and_postgresql_checks():
    sqlite_ddl = str(CreateTable(Team.__table__).compile(dialect=sqlite.dialect()))
    postgres_ddl = str(CreateTable(Team.__table__).compile(dialect=postgresql.dialect()))

    assert "json_valid(task_list)" in sqlite_ddl
    assert "json_type(task_list) = 'array'" in sqlite_ddl
    assert "json_array_length(task_list) <= 12" in sqlite_ddl
    assert f"length(CAST(task_list AS BLOB)) <= {TEAM_TASK_JSON_MAX_BYTES}" in sqlite_ddl
    assert "jsonb_typeof(task_list::jsonb) = 'array'" in postgres_ddl
    assert "jsonb_array_length(task_list::jsonb) <= 12" in postgres_ddl
    assert f"octet_length(task_list::text) <= {TEAM_TASK_JSON_MAX_BYTES}" in postgres_ddl
    assert "json_valid" not in postgres_ddl


POSTGRES_TEST_URL = (
    os.getenv("TEST_POSTGRES_URL")
    or os.getenv("POSTGRES_TEST_URL")
    or os.getenv("DATABASE_TEST_URL")
)


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="No test PostgreSQL URL configured")
def test_postgresql_task_check_rejects_raw_wrong_shape_count_and_size():
    engine = create_engine(POSTGRES_TEST_URL)
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            text(
                "CREATE TEMP TABLE campusmate_team_task_check ("
                "task_list JSON NOT NULL, "
                f"CONSTRAINT ck_team_task CHECK ({POSTGRESQL_TEAM_TASK_CHECK})) "
                "ON COMMIT DROP"
            )
        )
        valid = normalize_team_task_list(
            [{"id": "valid", "title": "🚀 valid", "done": False}]
        )
        connection.execute(
            text(
                "INSERT INTO campusmate_team_task_check (task_list) "
                "VALUES (CAST(:task_list AS JSON))"
            ),
            {"task_list": json.dumps(valid, ensure_ascii=True)},
        )
        invalid_values = (
            {"id": "object"},
            [{"id": str(index), "title": "task"} for index in range(13)],
            [{"id": "huge", "title": "x" * TEAM_TASK_JSON_MAX_BYTES}],
        )
        for invalid in invalid_values:
            with pytest.raises(DBAPIError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            "INSERT INTO campusmate_team_task_check (task_list) "
                            "VALUES (CAST(:task_list AS JSON))"
                        ),
                        {"task_list": json.dumps(invalid)},
                    )
        transaction.rollback()
