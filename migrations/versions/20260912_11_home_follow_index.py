"""Add a user-oriented topic follow index for the home feed.

Revision ID: 20260912_11
Revises: 20260912_10
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "20260912_11"
down_revision: Union[str, Sequence[str], None] = "20260912_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "ix_topic_follows_user_created"
INDEX_COLUMNS = ["user_id", "created_at", "topic_id"]


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "topic_follows" not in inspector.get_table_names():
        return
    indexes = {
        index["name"]: index for index in inspector.get_indexes("topic_follows")
    }
    existing = indexes.get(INDEX_NAME)
    if existing is not None and existing.get("column_names") != INDEX_COLUMNS:
        op.drop_index(INDEX_NAME, table_name="topic_follows")
        existing = None

    if existing is None:
        op.create_index(
            INDEX_NAME,
            "topic_follows",
            INDEX_COLUMNS,
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "topic_follows" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("topic_follows")}
    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name="topic_follows")
