"""Normalize legacy Post deadlines for chronological queries.

Revision ID: 20260913_15
Revises: 20260913_14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from services.deadlines import parse_deadline_at


revision: str = "20260913_15"
down_revision: Union[str, Sequence[str], None] = "20260913_14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKFILL_BATCH_SIZE = 500


def _column_names() -> set[str]:
    return {
        column["name"]
        for column in inspect(op.get_bind()).get_columns("posts")
    }


def _backfill_deadline_at() -> None:
    bind = op.get_bind()
    posts = sa.table(
        "posts",
        sa.column("id", sa.BigInteger()),
        sa.column("deadline", sa.Text()),
        sa.column("deadline_at", sa.DateTime(timezone=True)),
    )
    last_id: int | None = None
    while True:
        statement = (
            sa.select(posts.c.id, posts.c.deadline)
            .where(posts.c.deadline_at.is_(None))
            .order_by(posts.c.id)
            .limit(BACKFILL_BATCH_SIZE)
        )
        if last_id is not None:
            statement = statement.where(posts.c.id > last_id)
        rows = bind.execute(statement).mappings().all()
        if not rows:
            return
        bind.execute(
            posts.update()
            .where(posts.c.id == sa.bindparam("post_id"))
            .values(deadline_at=sa.bindparam("deadline_at")),
            [
                {
                    "post_id": row["id"],
                    "deadline_at": parse_deadline_at(row["deadline"]),
                }
                for row in rows
            ],
        )
        last_id = rows[-1]["id"]


def upgrade() -> None:
    if "posts" not in inspect(op.get_bind()).get_table_names():
        return
    columns = _column_names()
    if "deadline_at" not in columns:
        with op.batch_alter_table("posts") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "deadline_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                )
            )
    if "deadline" in columns:
        _backfill_deadline_at()


def downgrade() -> None:
    if "posts" not in inspect(op.get_bind()).get_table_names():
        return
    if "deadline_at" in _column_names():
        with op.batch_alter_table("posts") as batch_op:
            batch_op.drop_column("deadline_at")
