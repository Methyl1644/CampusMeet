from __future__ import annotations

from sqlalchemy import create_engine, inspect

from storage.database.models import (
    AccountRestriction,
    Appeal,
    ModerationCase,
    ModerationEvent,
    Report,
    UserBlock,
)
from storage.database.shared.model import Base


def _foreign_keys(table) -> set[tuple[str, str]]:
    return {
        (column.parent.name, column.target_fullname)
        for constraint in table.foreign_key_constraints
        for column in constraint.elements
    }


def test_moderation_models_create_the_complete_governance_schema():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    tables = set(inspect(engine).get_table_names())

    assert {
        "moderation_events",
        "reports",
        "user_blocks",
        "moderation_cases",
        "account_restrictions",
        "appeals",
    } <= tables


def test_moderation_event_can_only_store_masked_excerpt_and_rule_identifiers():
    columns = set(ModerationEvent.__table__.columns.keys())

    assert {"excerpt", "rule_ids"} <= columns
    assert not ({"content", "message", "evidence", "raw_text", "description"} & columns)


def test_report_and_user_block_models_enforce_supported_relations_and_active_uniqueness():
    report_columns = set(Report.__table__.columns.keys())
    block_indexes = {index.name: index for index in UserBlock.__table__.indexes}

    assert {"target_type", "target_id", "report_count", "status", "resolved_at"} <= report_columns
    assert "uq_open_report_per_reporter_target" in {index.name for index in Report.__table__.indexes}
    assert block_indexes["uq_active_user_block"].unique is True
    assert {
        ("reporter_id", "users.id"),
        ("assigned_operator_id", "users.id"),
    } <= _foreign_keys(Report.__table__)
    assert {
        ("blocker_id", "users.id"),
        ("blocked_id", "users.id"),
    } <= _foreign_keys(UserBlock.__table__)


def test_case_restriction_and_appeal_models_link_the_full_lifecycle():
    assert {
        ("event_id", "moderation_events.id"),
        ("report_id", "reports.id"),
        ("subject_user_id", "users.id"),
        ("assigned_operator_id", "users.id"),
    } <= _foreign_keys(ModerationCase.__table__)
    assert {
        ("case_id", "moderation_cases.id"),
        ("user_id", "users.id"),
        ("created_by", "users.id"),
    } <= _foreign_keys(AccountRestriction.__table__)
    assert {
        ("case_id", "moderation_cases.id"),
        ("appellant_id", "users.id"),
        ("reviewed_by", "users.id"),
    } <= _foreign_keys(Appeal.__table__)
    assert "uq_appeal_per_case_appellant" in {
        constraint.name for constraint in Appeal.__table__.constraints
    }
