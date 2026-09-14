"""Backfill activity creators as managers.

Revision ID: 20260914_18
Revises: 20260913_17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260914_18"
down_revision = "20260913_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {"topics", "topic_collaborators"} <= tables:
        return

    topics = sa.table(
        "topics",
        sa.column("id", sa.BigInteger()),
        sa.column("created_by", sa.BigInteger()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    collaborators = sa.table(
        "topic_collaborators",
        sa.column("topic_id", sa.BigInteger()),
        sa.column("user_id", sa.BigInteger()),
        sa.column("role", sa.Text()),
        sa.column("status", sa.Text()),
        sa.column("granted_by", sa.BigInteger()),
        sa.column("accepted_at", sa.DateTime(timezone=True)),
    )
    missing_creator = ~sa.exists(
        sa.select(1).where(
            collaborators.c.topic_id == topics.c.id,
            collaborators.c.user_id == topics.c.created_by,
        )
    )
    rows = sa.select(
        topics.c.id,
        topics.c.created_by,
        sa.literal("manager"),
        sa.literal("active"),
        topics.c.created_by,
        topics.c.created_at,
    ).where(topics.c.created_by.is_not(None), missing_creator)
    op.execute(
        collaborators.insert().from_select(
            ["topic_id", "user_id", "role", "status", "granted_by", "accepted_at"],
            rows,
        )
    )


def downgrade() -> None:
    # Creator grants are durable authorization history and are intentionally retained.
    pass
