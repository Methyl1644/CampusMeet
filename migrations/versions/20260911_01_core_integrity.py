"""Add collaboration foreign keys and retry guards.

Revision ID: 20260911_01
Revises: 20260911_00
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260911_01"
down_revision: Union[str, Sequence[str], None] = "20260911_00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FOREIGN_KEYS = (
    ("posts", "fk_posts_topic", ("topic_id",), "topics", ("id",), "SET NULL"),
    ("posts", "fk_posts_author", ("author_id",), "users", ("id",), None),
    ("applications", "fk_applications_post", ("post_id",), "posts", ("id",), "CASCADE"),
    ("applications", "fk_applications_applicant", ("applicant_id",), "users", ("id",), None),
    ("conversations", "fk_conversations_post", ("post_id",), "posts", ("id",), "CASCADE"),
    ("conversations", "fk_conversations_author", ("post_author_id",), "users", ("id",), None),
    ("conversations", "fk_conversations_applicant", ("applicant_id",), "users", ("id",), None),
    ("conversations", "fk_conversations_application", ("application_id",), "applications", ("id",), "SET NULL"),
    ("messages", "fk_messages_conversation", ("conversation_id",), "conversations", ("id",), "CASCADE"),
    ("messages", "fk_messages_sender", ("sender_id",), "users", ("id",), None),
    ("teams", "fk_teams_post", ("post_id",), "posts", ("id",), "CASCADE"),
    ("team_members", "fk_team_members_team", ("team_id",), "teams", ("id",), "CASCADE"),
    ("team_members", "fk_team_members_user", ("user_id",), "users", ("id",), None),
)

INDEXES = (
    ("posts", "ix_posts_author_created", ("author_id", "created_at")),
    ("posts", "ix_posts_topic_status", ("topic_id", "status")),
    ("applications", "ix_applications_applicant_created", ("applicant_id", "created_at")),
    ("conversations", "ix_conversations_author_last", ("post_author_id", "last_message_at")),
    ("conversations", "ix_conversations_applicant_last", ("applicant_id", "last_message_at")),
    ("messages", "ix_messages_conversation_created", ("conversation_id", "created_at")),
    ("team_members", "ix_team_members_user", ("user_id",)),
)


def _has_fk(table_name: str, columns: tuple[str, ...], referred_table: str) -> bool:
    return any(
        tuple(item["constrained_columns"]) == columns and item["referred_table"] == referred_table
        for item in inspect(op.get_bind()).get_foreign_keys(table_name)
    )


def _has_unique(table_name: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_unique_constraints(table_name))


def _has_index(table_name: str, name: str) -> bool:
    return any(item.get("name") == name for item in inspect(op.get_bind()).get_indexes(table_name))


def _assert_no_duplicate_active_applications() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            "SELECT post_id, applicant_id FROM applications "
            "WHERE status IN ('pending', 'accepted') "
            "GROUP BY post_id, applicant_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot add the active-application guard while duplicate active applications exist "
            f"for post_id={duplicate.post_id}, applicant_id={duplicate.applicant_id}."
        )


def _assert_no_duplicate_conversations() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            "SELECT application_id FROM conversations WHERE application_id IS NOT NULL "
            "GROUP BY application_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot add the conversation retry guard while duplicate conversations exist "
            f"for application_id={duplicate.application_id}."
        )


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    dialect = op.get_bind().dialect.name

    for table, name, columns, referred_table, referred_columns, ondelete in FOREIGN_KEYS:
        if table not in tables or referred_table not in tables or _has_fk(table, columns, referred_table):
            continue
        if dialect == "sqlite":
            with op.batch_alter_table(table) as batch:
                batch.create_foreign_key(name, referred_table, list(columns), list(referred_columns), ondelete=ondelete)
        else:
            op.create_foreign_key(name, table, referred_table, list(columns), list(referred_columns), ondelete=ondelete)

    if "applications" in tables and not _has_index("applications", "uq_active_application_per_post_user"):
        _assert_no_duplicate_active_applications()
        op.create_index(
            "uq_active_application_per_post_user",
            "applications",
            ["post_id", "applicant_id"],
            unique=True,
            sqlite_where=sa.text("status IN ('pending', 'accepted')"),
            postgresql_where=sa.text("status IN ('pending', 'accepted')"),
        )

    if "conversations" in tables and not _has_unique("conversations", "uq_conversation_application"):
        _assert_no_duplicate_conversations()
        with op.batch_alter_table("conversations") as batch:
            batch.create_unique_constraint("uq_conversation_application", ["application_id"])

    for table, name, columns in INDEXES:
        if table in tables and not _has_index(table, name):
            op.create_index(name, table, list(columns), unique=False)


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    dialect = op.get_bind().dialect.name

    for table, name, _ in reversed(INDEXES):
        if table in tables and _has_index(table, name):
            op.drop_index(name, table_name=table)
    if "conversations" in tables and _has_unique("conversations", "uq_conversation_application"):
        with op.batch_alter_table("conversations") as batch:
            batch.drop_constraint("uq_conversation_application", type_="unique")
    if "applications" in tables and _has_index("applications", "uq_active_application_per_post_user"):
        op.drop_index("uq_active_application_per_post_user", table_name="applications")

    for table, name, columns, referred_table, _, _ in reversed(FOREIGN_KEYS):
        if table not in tables or not _has_fk(table, columns, referred_table):
            continue
        if dialect == "sqlite":
            with op.batch_alter_table(table) as batch:
                batch.drop_constraint(name, type_="foreignkey")
        else:
            op.drop_constraint(name, table, type_="foreignkey")
