"""Persist user onboarding state and profile details.

Revision ID: 20260912_10
Revises: 20260912_09
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260912_10"
down_revision: Union[str, Sequence[str], None] = "20260912_09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_columns = {
        column["name"] for column in inspect(op.get_bind()).get_columns("users")
    }
    onboarding_columns = (
        sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True)),
        sa.Column("bio", sa.Text()),
        sa.Column("interests", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("looking_for", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("availability", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("profile_visibility", sa.JSON(), nullable=False, server_default="{}"),
    )
    for column in onboarding_columns:
        if column.name not in existing_columns:
            op.add_column("users", column)

    if {"nickname", "major", "grade"} <= existing_columns:
        users = sa.table(
            "users",
            sa.column("nickname", sa.Text()),
            sa.column("major", sa.Text()),
            sa.column("grade", sa.Text()),
            sa.column("onboarding_completed_at", sa.DateTime(timezone=True)),
        )
        op.execute(
            users.update()
            .where(
                users.c.onboarding_completed_at.is_(None),
                sa.func.trim(users.c.nickname) != "",
                sa.func.trim(users.c.major) != "",
                sa.func.trim(users.c.grade) != "",
            )
            .values(onboarding_completed_at=sa.func.now())
        )

    temporary_default_names = (
        "onboarding_step",
        "interests",
        "looking_for",
        "availability",
        "profile_visibility",
    )
    columns_after_backfill = {
        column["name"]: column
        for column in inspect(op.get_bind()).get_columns("users")
    }
    defaults_to_remove = (
        name
        for name in temporary_default_names
        if columns_after_backfill[name].get("default") is not None
    )
    with op.batch_alter_table("users") as batch_op:
        for name in defaults_to_remove:
            batch_op.alter_column(name, server_default=None)


def downgrade() -> None:
    raise RuntimeError("Onboarding state is intentionally retained.")
