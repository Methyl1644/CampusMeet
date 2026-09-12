"""Add message read state and team ownership lifecycle.

Revision ID: 20260912_06
Revises: 20260911_05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260912_06"
down_revision: Union[str, Sequence[str], None] = "20260911_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_missing(table: str, columns: dict[str, sa.Column]) -> None:
    existing = {item["name"] for item in inspect(op.get_bind()).get_columns(table)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "messages" in tables:
        _add_missing(
            "messages",
            {"read_at": sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)},
        )
    if "teams" in tables:
        _add_missing(
            "teams",
            {
                "owner_id": sa.Column("owner_id", sa.BigInteger(), nullable=True),
                "status": sa.Column("status", sa.Text(), nullable=False, server_default="active"),
                "updated_at": sa.Column(
                    "updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()
                ),
            },
        )
        op.execute(
            sa.text(
                "UPDATE teams SET owner_id = (SELECT posts.author_id FROM posts WHERE posts.id = teams.post_id) "
                "WHERE owner_id IS NULL"
            )
        )
    if "team_members" in tables:
        _add_missing(
            "team_members",
            {"member_role": sa.Column("member_role", sa.Text(), nullable=False, server_default="member")},
        )
        op.execute(
            sa.text(
                "UPDATE team_members SET member_role = 'owner' WHERE EXISTS ("
                "SELECT 1 FROM teams WHERE teams.id = team_members.team_id "
                "AND teams.owner_id = team_members.user_id)"
            )
        )


def downgrade() -> None:
    raise RuntimeError("Conversation and team lifecycle history is intentionally retained.")
