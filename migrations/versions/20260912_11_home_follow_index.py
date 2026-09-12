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


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "topic_follows" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("topic_follows")}
    if INDEX_NAME not in indexes:
        op.create_index(
            INDEX_NAME,
            "topic_follows",
            ["user_id", "created_at", "topic_id"],
        )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="topic_follows")
