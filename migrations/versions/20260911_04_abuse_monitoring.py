"""Add privacy-safe behavioral abuse events.

Revision ID: 20260911_04
Revises: 20260911_03
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260911_04"
down_revision: Union[str, Sequence[str], None] = "20260911_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "abuse_events" in inspector.get_table_names():
        return
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "abuse_events",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column("content_fingerprint", sa.Text(), nullable=True),
        sa.Column("network_hash", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False, server_default="allow"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_abuse_events_user_type_created",
        "abuse_events",
        ["user_id", "event_type", "created_at"],
    )
    op.create_index(
        "ix_abuse_events_network_type_created",
        "abuse_events",
        ["network_hash", "event_type", "created_at"],
    )
    op.create_index(
        "ix_abuse_events_fingerprint_created",
        "abuse_events",
        ["content_fingerprint", "created_at"],
    )


def downgrade() -> None:
    raise RuntimeError("Abuse monitoring history is intentionally retained.")
