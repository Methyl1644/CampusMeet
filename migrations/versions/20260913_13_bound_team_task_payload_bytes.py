"""Bound team task payload shape and serialized bytes.

Revision ID: 20260913_13
Revises: 20260913_12
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from storage.database.models.team import (
    POSTGRESQL_TEAM_TASK_CHECK,
    SQLITE_TEAM_TASK_CHECK,
    normalize_team_task_list,
)


revision: str = "20260913_13"
down_revision: Union[str, Sequence[str], None] = "20260913_12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "teams"
CONSTRAINT_NAME = "ck_teams_task_list_bounded"
LEGACY_TASK_COUNT_CHECK = "json_array_length(task_list) <= 12"


def _constraint_sql(dialect_name: str) -> str:
    if dialect_name == "sqlite":
        return SQLITE_TEAM_TASK_CHECK
    if dialect_name == "postgresql":
        return POSTGRESQL_TEAM_TASK_CHECK
    raise RuntimeError(f"Unsupported database dialect for team task bounds: {dialect_name}")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    teams = sa.table(
        TABLE_NAME,
        sa.column("id", sa.BigInteger()),
        sa.column("task_list", sa.JSON()),
    )
    rows = bind.execute(sa.select(teams.c.id, teams.c.task_list))
    for team_id, task_list in rows:
        normalized = normalize_team_task_list(task_list)
        if normalized != task_list:
            bind.execute(
                teams.update().where(teams.c.id == team_id).values(task_list=normalized)
            )

    constraint_names = {
        constraint["name"]
        for constraint in inspect(bind).get_check_constraints(TABLE_NAME)
    }
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if CONSTRAINT_NAME in constraint_names:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
        batch_op.create_check_constraint(
            CONSTRAINT_NAME,
            _constraint_sql(bind.dialect.name),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return

    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints(TABLE_NAME)
    }
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if CONSTRAINT_NAME in constraint_names:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
        batch_op.create_check_constraint(CONSTRAINT_NAME, LEGACY_TASK_COUNT_CHECK)
