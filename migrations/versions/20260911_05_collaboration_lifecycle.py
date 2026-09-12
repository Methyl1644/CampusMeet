"""Add post and application lifecycle timestamps.

Revision ID: 20260911_05
Revises: 20260911_04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260911_05"
down_revision: Union[str, Sequence[str], None] = "20260911_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_missing(table: str, columns: dict[str, sa.Column]) -> None:
    existing = {item["name"] for item in inspect(op.get_bind()).get_columns(table)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    tables = set(inspect(op.get_bind()).get_table_names())
    if "posts" in tables:
        _add_missing(
            "posts",
            {
                "closed_at": sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
                "archived_at": sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
                "deleted_at": sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            },
        )
    if "applications" in tables:
        _add_missing(
            "applications",
            {
                "withdrawn_at": sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
                "updated_at": sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                    server_default=sa.func.now(),
                ),
            },
        )


def downgrade() -> None:
    raise RuntimeError("Lifecycle history is intentionally retained.")
