"""Bound persisted team task lists before home-feed reads.

Revision ID: 20260913_12
Revises: 20260912_11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260913_12"
down_revision: Union[str, Sequence[str], None] = "20260912_11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "teams"
CONSTRAINT_NAME = "ck_teams_task_list_bounded"
TEAM_TASK_LIMIT = 12


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
    for team_id, task_list in bind.execute(sa.select(teams.c.id, teams.c.task_list)):
        bounded = task_list[:TEAM_TASK_LIMIT] if isinstance(task_list, list) else []
        if bounded != task_list:
            bind.execute(
                teams.update().where(teams.c.id == team_id).values(task_list=bounded)
            )

    constraint_names = {
        constraint["name"]
        for constraint in inspect(bind).get_check_constraints(TABLE_NAME)
    }
    if CONSTRAINT_NAME not in constraint_names:
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.create_check_constraint(
                CONSTRAINT_NAME,
                f"json_array_length(task_list) <= {TEAM_TASK_LIMIT}",
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
    if CONSTRAINT_NAME in constraint_names:
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
