from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from storage.database.models import *  # noqa: F403 - imports register every model
from storage.database.shared.model import Base


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = set(Base.metadata.tables)


def _alembic_config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_alembic_upgrade_builds_the_current_schema_in_an_empty_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'empty.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    tables = set(inspect(create_engine(database_url)).get_table_names())
    assert EXPECTED_TABLES <= tables
    assert "alembic_version" in tables


def test_alembic_upgrade_adopts_an_existing_schema_without_recreating_tables(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    command.upgrade(_alembic_config(database_url), "head")
    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    assert inspector.get_columns("users")
    assert inspector.get_columns("posts")
    assert "alembic_version" in inspector.get_table_names()


def test_auth_onboarding_migration_adds_user_profile_columns(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'onboarding.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, major TEXT, grade TEXT)"
            )
        )
    command.stamp(_alembic_config(database_url), "20260912_09")

    command.upgrade(_alembic_config(database_url), "head")

    names = {item["name"] for item in inspect(engine).get_columns("users")}
    assert {
        "onboarding_step",
        "onboarding_completed_at",
        "bio",
        "interests",
        "looking_for",
        "availability",
        "profile_visibility",
    } <= names


def test_auth_onboarding_migration_backfills_only_complete_profiles(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'onboarding-backfill.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, major TEXT, grade TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (id, nickname, major, grade) VALUES "
                "(1, 'Complete', 'Software', '2026'), "
                "(2, 'Blank', '   ', '2026')"
            )
        )
    command.stamp(_alembic_config(database_url), "20260912_09")

    command.upgrade(_alembic_config(database_url), "head")

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, onboarding_step, onboarding_completed_at, interests, looking_for, "
                "availability, profile_visibility FROM users ORDER BY id"
            )
        ).all()
    assert rows[0][1:] == (1, rows[0].onboarding_completed_at, "[]", "[]", "{}", "{}")
    assert rows[0].onboarding_completed_at is not None
    assert rows[1][1:] == (1, None, "[]", "[]", "{}", "{}")


def test_auth_onboarding_migration_matches_fresh_schema_server_defaults(tmp_path):
    fresh_database_url = f"sqlite:///{tmp_path / 'onboarding-fresh.db'}"
    command.upgrade(_alembic_config(fresh_database_url), "head")
    fresh_columns = {
        item["name"]: item
        for item in inspect(create_engine(fresh_database_url)).get_columns("users")
    }

    upgraded_database_url = f"sqlite:///{tmp_path / 'onboarding-upgraded.db'}"
    upgraded_engine = create_engine(upgraded_database_url)
    with upgraded_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, nickname TEXT NOT NULL, major TEXT, grade TEXT)"
            )
        )
    command.stamp(_alembic_config(upgraded_database_url), "20260912_09")
    command.upgrade(_alembic_config(upgraded_database_url), "head")
    upgraded_columns = {
        item["name"]: item for item in inspect(upgraded_engine).get_columns("users")
    }

    names = {
        "onboarding_step",
        "interests",
        "looking_for",
        "availability",
        "profile_visibility",
    }
    fresh_defaults = {name: fresh_columns[name]["default"] for name in names}
    upgraded_defaults = {name: upgraded_columns[name]["default"] for name in names}

    assert upgraded_defaults == fresh_defaults
    assert set(upgraded_defaults.values()) == {None}


def test_home_feed_migration_adds_user_oriented_topic_follow_index(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'home-feed-index.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE topic_follows ("
                "topic_id INTEGER NOT NULL, user_id INTEGER NOT NULL, created_at DATETIME NOT NULL, "
                "PRIMARY KEY (topic_id, user_id))"
            )
        )
    command.stamp(_alembic_config(database_url), "20260912_10")

    before = {index["name"] for index in inspect(engine).get_indexes("topic_follows")}
    assert "ix_topic_follows_user_created" not in before

    command.upgrade(_alembic_config(database_url), "head")

    indexes = {index["name"]: index for index in inspect(engine).get_indexes("topic_follows")}
    assert indexes["ix_topic_follows_user_created"]["column_names"] == [
        "user_id",
        "created_at",
        "topic_id",
    ]


def test_home_feed_migration_replaces_same_named_index_with_wrong_columns(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'home-feed-wrong-index.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE topic_follows ("
                "topic_id INTEGER NOT NULL, user_id INTEGER NOT NULL, created_at DATETIME NOT NULL, "
                "PRIMARY KEY (topic_id, user_id))"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_topic_follows_user_created "
                "ON topic_follows (topic_id)"
            )
        )
    command.stamp(_alembic_config(database_url), "20260912_10")

    command.upgrade(_alembic_config(database_url), "head")

    indexes = {index["name"]: index for index in inspect(engine).get_indexes("topic_follows")}
    assert indexes["ix_topic_follows_user_created"]["column_names"] == [
        "user_id",
        "created_at",
        "topic_id",
    ]


def test_home_feed_migration_noops_and_downgrades_when_follow_table_is_absent(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'home-feed-no-follow-table.db'}"
    engine = create_engine(database_url)
    command.stamp(_alembic_config(database_url), "20260912_10")

    command.upgrade(_alembic_config(database_url), "head")
    command.downgrade(_alembic_config(database_url), "20260912_10")

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "20260912_10"
    assert "topic_follows" not in inspect(engine).get_table_names()


def test_identity_migration_preserves_legacy_organization_application_rows(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'legacy-identity.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE organizations (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE organization_members ("
                "id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
                "role TEXT NOT NULL, status TEXT NOT NULL, expires_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE organization_applications ("
                "id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL, organization_name TEXT NOT NULL, "
                "org_type TEXT NOT NULL, official_email TEXT, evidence TEXT NOT NULL, "
                "status TEXT NOT NULL, reviewed_by INTEGER, reviewed_at DATETIME, created_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (id) VALUES (1), (2); "
            )
        )
        connection.execute(
            text(
                "INSERT INTO organization_applications "
                "(id, applicant_id, organization_name, org_type, official_email, evidence, status) "
                "VALUES (9, 1, '南京大学羽毛球协会', 'student_club', 'club@nju.edu.cn', "
                "'legacy-proof', 'pending')"
            )
        )

    command.stamp(_alembic_config(database_url), "20260911_01")
    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(engine)
    columns = {item["name"] for item in inspector.get_columns("organization_applications")}
    assert {
        "school_scope",
        "official_page",
        "responsible_person_statement",
        "evidence_reference",
        "review_reason",
        "expires_at",
    } <= columns
    assert {
        "organization_invitations",
        "platform_role_grants",
        "organization_ownership_transfers",
    } <= set(inspector.get_table_names())
    application_indexes = {
        item["name"]: item for item in inspector.get_indexes("organization_applications")
    }
    assert application_indexes["uq_pending_organization_application"]["unique"] == 1
    member_indexes = {item["name"]: item for item in inspector.get_indexes("organization_members")}
    assert member_indexes["uq_active_organization_owner"]["unique"] == 1

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT organization_name, evidence, status "
                "FROM organization_applications WHERE id = 9"
            )
        ).one()
    assert tuple(row) == ("南京大学羽毛球协会", "legacy-proof", "pending")


def test_identity_migration_refuses_duplicate_active_records_without_deleting_them(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'duplicate-identity.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE organizations (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE organization_members ("
                "id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
                "role TEXT NOT NULL, status TEXT NOT NULL, expires_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE organization_applications ("
                "id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL, organization_name TEXT NOT NULL, "
                "org_type TEXT NOT NULL, official_email TEXT, evidence TEXT NOT NULL, "
                "status TEXT NOT NULL, reviewed_by INTEGER, reviewed_at DATETIME, created_at DATETIME)"
            )
        )
        connection.execute(text("INSERT INTO users (id) VALUES (1), (2), (3)"))
        connection.execute(text("INSERT INTO organizations (id) VALUES (5)"))
        connection.execute(
            text(
                "INSERT INTO organization_members "
                "(id, organization_id, user_id, role, status) VALUES "
                "(1, 5, 1, 'owner', 'active'), (2, 5, 2, 'owner', 'active')"
            )
        )

    command.stamp(_alembic_config(database_url), "20260911_01")
    try:
        command.upgrade(_alembic_config(database_url), "head")
    except RuntimeError as exc:
        assert "multiple active owners" in str(exc)
    else:
        raise AssertionError("migration should refuse duplicate active owners")

    with engine.connect() as connection:
        owner_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM organization_members "
                "WHERE organization_id = 5 AND role = 'owner' AND status = 'active'"
            )
        ).scalar_one()
    assert owner_count == 2


def test_identity_migration_refuses_duplicate_pending_applications_without_deleting_them(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'duplicate-applications.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE organizations (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE organization_members ("
                "id INTEGER PRIMARY KEY, organization_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
                "role TEXT NOT NULL, status TEXT NOT NULL, expires_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE organization_applications ("
                "id INTEGER PRIMARY KEY, applicant_id INTEGER NOT NULL, organization_name TEXT NOT NULL, "
                "org_type TEXT NOT NULL, official_email TEXT, evidence TEXT NOT NULL, "
                "status TEXT NOT NULL, reviewed_by INTEGER, reviewed_at DATETIME, created_at DATETIME)"
            )
        )
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        connection.execute(
            text(
                "INSERT INTO organization_applications "
                "(id, applicant_id, organization_name, org_type, evidence, status) VALUES "
                "(1, 1, '同一社团', 'student_club', 'proof-a', 'pending'), "
                "(2, 1, '同一社团', 'student_club', 'proof-b', 'pending')"
            )
        )

    command.stamp(_alembic_config(database_url), "20260911_01")
    try:
        command.upgrade(_alembic_config(database_url), "head")
    except RuntimeError as exc:
        assert "duplicate pending organization applications" in str(exc)
    else:
        raise AssertionError("migration should refuse duplicate pending applications")

    with engine.connect() as connection:
        application_count = connection.execute(
            text("SELECT COUNT(*) FROM organization_applications")
        ).scalar_one()
    assert application_count == 2


def test_moderation_migration_upgrades_a_revision_02_database_idempotently(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'legacy-moderation.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))

    command.stamp(_alembic_config(database_url), "20260911_02")
    command.upgrade(_alembic_config(database_url), "head")
    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(engine)
    assert {
        "moderation_events",
        "reports",
        "user_blocks",
        "moderation_cases",
        "account_restrictions",
        "appeals",
    } <= set(inspector.get_table_names())
    assert "uq_open_report_per_reporter_target" in {
        index["name"] for index in inspector.get_indexes("reports")
    }
    assert "uq_active_user_block" in {
        index["name"] for index in inspector.get_indexes("user_blocks")
    }

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 1


def test_render_runs_migrations_before_starting_the_api():
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "alembic upgrade head" in blueprint
    assert blueprint.index("alembic upgrade head") < blueprint.index("python src/main.py")
