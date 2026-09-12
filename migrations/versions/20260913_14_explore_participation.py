"""Add the Explore participation domain.

Revision ID: 20260913_14
Revises: 20260913_13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260913_14"
down_revision: Union[str, Sequence[str], None] = "20260913_13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TOPIC_PARTICIPATION_CHECK = "ck_topics_participation_mode"
TOPIC_CAPACITY_CHECK = "ck_topics_capacity_positive"
POST_PURPOSE_CHECK = "ck_posts_purpose"
POST_JOIN_MODE_CHECK = "ck_posts_join_mode"
OFFICIAL_SIGNUP_INDEX = "uq_posts_effective_official_signup_topic"
BOOKMARK_INDEX = "ix_post_bookmarks_user_created"

TOPIC_PARTICIPATION_SQL = (
    "participation_mode IN ('open_team', 'official_signup', 'information_only')"
)
TOPIC_CAPACITY_SQL = "capacity IS NULL OR capacity > 0"
POST_PURPOSE_SQL = (
    "purpose IN ('team_recruitment', 'official_signup', 'discussion')"
)
POST_JOIN_MODE_SQL = "join_mode IN ('application', 'direct', 'none')"
OFFICIAL_SIGNUP_PREDICATE = (
    "topic_id IS NOT NULL AND purpose = 'official_signup' "
    "AND status IN ('recruiting', 'full')"
)


def _column_map(table_name: str) -> dict[str, dict]:
    return {
        column["name"]: column
        for column in inspect(op.get_bind()).get_columns(table_name)
    }


def _check_names(table_name: str) -> set[str | None]:
    return {
        constraint.get("name")
        for constraint in inspect(op.get_bind()).get_check_constraints(table_name)
    }


def _index_names(table_name: str) -> set[str | None]:
    return {
        index.get("name")
        for index in inspect(op.get_bind()).get_indexes(table_name)
    }


def _upgrade_topics() -> None:
    columns = _column_map("topics")
    missing = {
        "location_name": sa.Column("location_name", sa.Text(), nullable=True),
        "campus_scope": sa.Column("campus_scope", sa.Text(), nullable=True),
        "capacity": sa.Column("capacity", sa.Integer(), nullable=True),
        "participation_mode": sa.Column(
            "participation_mode",
            sa.Text(),
            nullable=True,
        ),
    }
    with op.batch_alter_table("topics") as batch_op:
        for name, column in missing.items():
            if name not in columns:
                batch_op.add_column(column)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE topics SET participation_mode = 'open_team' "
            "WHERE participation_mode IS NULL "
            "OR participation_mode NOT IN ('open_team', 'official_signup', 'information_only')"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE topics SET capacity = NULL "
            "WHERE capacity IS NOT NULL AND capacity <= 0"
        )
    )

    columns = _column_map("topics")
    checks = _check_names("topics")
    with op.batch_alter_table("topics") as batch_op:
        if columns["participation_mode"]["nullable"]:
            batch_op.alter_column(
                "participation_mode",
                existing_type=sa.Text(),
                nullable=False,
            )
        if TOPIC_PARTICIPATION_CHECK not in checks:
            batch_op.create_check_constraint(
                TOPIC_PARTICIPATION_CHECK,
                TOPIC_PARTICIPATION_SQL,
            )
        if TOPIC_CAPACITY_CHECK not in checks:
            batch_op.create_check_constraint(
                TOPIC_CAPACITY_CHECK,
                TOPIC_CAPACITY_SQL,
            )


def _upgrade_posts() -> None:
    columns = _column_map("posts")
    missing = {
        "cover_url": sa.Column("cover_url", sa.Text(), nullable=True),
        "purpose": sa.Column("purpose", sa.Text(), nullable=True),
        "join_mode": sa.Column("join_mode", sa.Text(), nullable=True),
    }
    with op.batch_alter_table("posts") as batch_op:
        for name, column in missing.items():
            if name not in columns:
                batch_op.add_column(column)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE posts SET purpose = 'team_recruitment' "
            "WHERE purpose IS NULL "
            "OR purpose NOT IN ('team_recruitment', 'official_signup', 'discussion')"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE posts SET join_mode = 'application' "
            "WHERE join_mode IS NULL OR join_mode NOT IN ('application', 'direct', 'none')"
        )
    )

    duplicate = bind.execute(
        sa.text(
            "SELECT topic_id FROM posts WHERE topic_id IS NOT NULL "
            "AND purpose = 'official_signup' AND status IN ('recruiting', 'full') "
            "GROUP BY topic_id HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot add the official-signup guard while multiple effective signup posts "
            f"exist for topic_id={duplicate.topic_id}."
        )

    columns = _column_map("posts")
    checks = _check_names("posts")
    with op.batch_alter_table("posts") as batch_op:
        if columns["purpose"]["nullable"]:
            batch_op.alter_column("purpose", existing_type=sa.Text(), nullable=False)
        if columns["join_mode"]["nullable"]:
            batch_op.alter_column("join_mode", existing_type=sa.Text(), nullable=False)
        if POST_PURPOSE_CHECK not in checks:
            batch_op.create_check_constraint(POST_PURPOSE_CHECK, POST_PURPOSE_SQL)
        if POST_JOIN_MODE_CHECK not in checks:
            batch_op.create_check_constraint(POST_JOIN_MODE_CHECK, POST_JOIN_MODE_SQL)

    if OFFICIAL_SIGNUP_INDEX not in _index_names("posts"):
        op.create_index(
            OFFICIAL_SIGNUP_INDEX,
            "posts",
            ["topic_id"],
            unique=True,
            sqlite_where=sa.text(OFFICIAL_SIGNUP_PREDICATE),
            postgresql_where=sa.text(OFFICIAL_SIGNUP_PREDICATE),
        )


def _upgrade_post_bookmarks() -> None:
    if "post_bookmarks" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "post_bookmarks",
            sa.Column(
                "post_id",
                sa.BigInteger(),
                sa.ForeignKey("posts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.BigInteger(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("post_id", "user_id", name="pk_post_bookmarks"),
        )
    if BOOKMARK_INDEX not in _index_names("post_bookmarks"):
        op.create_index(
            BOOKMARK_INDEX,
            "post_bookmarks",
            ["user_id", "created_at", "post_id"],
            unique=False,
        )


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "topics" in tables:
        _upgrade_topics()
    if "posts" in tables:
        _upgrade_posts()
    if {"posts", "users"} <= tables:
        _upgrade_post_bookmarks()


def downgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "post_bookmarks" in tables:
        op.drop_table("post_bookmarks")

    if "posts" in tables:
        if OFFICIAL_SIGNUP_INDEX in _index_names("posts"):
            op.drop_index(OFFICIAL_SIGNUP_INDEX, table_name="posts")
        columns = _column_map("posts")
        checks = _check_names("posts")
        with op.batch_alter_table("posts") as batch_op:
            if POST_JOIN_MODE_CHECK in checks:
                batch_op.drop_constraint(POST_JOIN_MODE_CHECK, type_="check")
            if POST_PURPOSE_CHECK in checks:
                batch_op.drop_constraint(POST_PURPOSE_CHECK, type_="check")
            for name in ("join_mode", "purpose", "cover_url"):
                if name in columns:
                    batch_op.drop_column(name)

    if "topics" in tables:
        columns = _column_map("topics")
        checks = _check_names("topics")
        with op.batch_alter_table("topics") as batch_op:
            if TOPIC_CAPACITY_CHECK in checks:
                batch_op.drop_constraint(TOPIC_CAPACITY_CHECK, type_="check")
            if TOPIC_PARTICIPATION_CHECK in checks:
                batch_op.drop_constraint(TOPIC_PARTICIPATION_CHECK, type_="check")
            for name in (
                "participation_mode",
                "capacity",
                "campus_scope",
                "location_name",
            ):
                if name in columns:
                    batch_op.drop_column(name)
