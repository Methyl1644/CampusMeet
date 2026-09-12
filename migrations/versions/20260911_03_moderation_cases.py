"""Add moderation records, reporting, blocking, restrictions, and appeals.

Revision ID: 20260911_03
Revises: 20260911_02
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260911_03"
down_revision: Union[str, Sequence[str], None] = "20260911_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    return {item["name"] for item in inspect(op.get_bind()).get_indexes(table_name)}


def _create_tables() -> None:
    tables = _tables()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

    if "moderation_events" not in tables:
        op.create_table(
            "moderation_events",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("surface", sa.Text(), nullable=False),
            sa.Column("target_type", sa.Text(), nullable=True),
            sa.Column("target_id", sa.Text(), nullable=True),
            sa.Column("actor_id", sa.BigInteger(), nullable=True),
            sa.Column("action", sa.Text(), nullable=False),
            sa.Column("risk_level", sa.Text(), nullable=False),
            sa.Column("rule_ids", sa.JSON(), nullable=False),
            sa.Column("excerpt", sa.Text(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False, server_default="rules"),
            sa.Column("status", sa.Text(), nullable=False, server_default="recorded"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(
                ["actor_id"], ["users.id"], name="fk_moderation_events_actor", ondelete="SET NULL"
            ),
        )

    if "reports" not in tables:
        op.create_table(
            "reports",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("reporter_id", sa.BigInteger(), nullable=False),
            sa.Column("target_type", sa.Text(), nullable=False),
            sa.Column("target_id", sa.Text(), nullable=False),
            sa.Column("reason_code", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("report_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.Text(), nullable=False, server_default="open"),
            sa.Column("assigned_operator_id", sa.BigInteger(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], name="fk_reports_reporter"),
            sa.ForeignKeyConstraint(
                ["assigned_operator_id"],
                ["users.id"],
                name="fk_reports_assigned_operator",
                ondelete="SET NULL",
            ),
        )

    if "user_blocks" not in tables:
        op.create_table(
            "user_blocks",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("blocker_id", sa.BigInteger(), nullable=False),
            sa.Column("blocked_id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], name="fk_user_blocks_blocker"),
            sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], name="fk_user_blocks_blocked"),
        )

    if "moderation_cases" not in tables:
        op.create_table(
            "moderation_cases",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("event_id", sa.BigInteger(), nullable=True),
            sa.Column("report_id", sa.BigInteger(), nullable=True),
            sa.Column("target_type", sa.Text(), nullable=False),
            sa.Column("target_id", sa.Text(), nullable=False),
            sa.Column("subject_user_id", sa.BigInteger(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="open"),
            sa.Column("priority", sa.Text(), nullable=False, server_default="normal"),
            sa.Column("reason_code", sa.Text(), nullable=False),
            sa.Column("assigned_operator_id", sa.BigInteger(), nullable=True),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["event_id"], ["moderation_events.id"], name="fk_moderation_cases_event", ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["report_id"], ["reports.id"], name="fk_moderation_cases_report", ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["subject_user_id"], ["users.id"], name="fk_moderation_cases_subject", ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["assigned_operator_id"],
                ["users.id"],
                name="fk_moderation_cases_assigned_operator",
                ondelete="SET NULL",
            ),
        )

    if "account_restrictions" not in tables:
        op.create_table(
            "account_restrictions",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("case_id", sa.BigInteger(), nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("restriction_type", sa.Text(), nullable=False),
            sa.Column("reason_code", sa.Text(), nullable=False),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by", sa.BigInteger(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_by", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["case_id"], ["moderation_cases.id"], name="fk_restrictions_case"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_restrictions_user"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_restrictions_creator"),
            sa.ForeignKeyConstraint(
                ["revoked_by"], ["users.id"], name="fk_restrictions_revoker", ondelete="SET NULL"
            ),
        )

    if "appeals" not in tables:
        op.create_table(
            "appeals",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("case_id", sa.BigInteger(), nullable=False),
            sa.Column("appellant_id", sa.BigInteger(), nullable=False),
            sa.Column("statement", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["case_id"], ["moderation_cases.id"], name="fk_appeals_case"),
            sa.ForeignKeyConstraint(["appellant_id"], ["users.id"], name="fk_appeals_appellant"),
            sa.ForeignKeyConstraint(
                ["reviewed_by"], ["users.id"], name="fk_appeals_reviewer", ondelete="SET NULL"
            ),
            sa.UniqueConstraint("case_id", "appellant_id", name="uq_appeal_per_case_appellant"),
        )


def _create_indexes() -> None:
    index_specs = {
        "moderation_events": (
            ("ix_moderation_events_target_created", ["target_type", "target_id", "created_at"], False, None),
            ("ix_moderation_events_actor_created", ["actor_id", "created_at"], False, None),
        ),
        "reports": (
            (
                "uq_open_report_per_reporter_target",
                ["reporter_id", "target_type", "target_id"],
                True,
                "status = 'open'",
            ),
            ("ix_reports_reporter_created", ["reporter_id", "created_at"], False, None),
            ("ix_reports_status_created", ["status", "created_at"], False, None),
        ),
        "user_blocks": (
            ("uq_active_user_block", ["blocker_id", "blocked_id"], True, "revoked_at IS NULL"),
            ("ix_user_blocks_blocked_active", ["blocked_id", "revoked_at"], False, None),
        ),
        "moderation_cases": (
            ("ix_moderation_cases_queue", ["status", "priority", "created_at"], False, None),
            ("ix_moderation_cases_target", ["target_type", "target_id"], False, None),
        ),
        "account_restrictions": (
            ("ix_account_restrictions_user_expiry", ["user_id", "expires_at"], False, None),
            ("ix_account_restrictions_case", ["case_id"], False, None),
        ),
        "appeals": (("ix_appeals_status_created", ["status", "created_at"], False, None),),
    }
    for table_name, specs in index_specs.items():
        existing = _index_names(table_name)
        for name, columns, unique, predicate in specs:
            if name in existing:
                continue
            kwargs = {}
            if predicate:
                kwargs = {
                    "sqlite_where": sa.text(predicate),
                    "postgresql_where": sa.text(predicate),
                }
            op.create_index(name, table_name, columns, unique=unique, **kwargs)


def upgrade() -> None:
    if "users" not in _tables():
        raise RuntimeError("Moderation migration requires the existing users table")
    _create_tables()
    _create_indexes()


def downgrade() -> None:
    raise RuntimeError(
        "Moderation migration is intentionally irreversible because dropping it would delete review history."
    )
