"""Add bounded user notification preferences.

Revision ID: 20260913_16
Revises: 20260913_15
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from services.onboarding import normalize_notification_preferences
from storage.database.models.user import (
    POSTGRESQL_NOTIFICATION_PREFERENCES_CHECK,
    SQLITE_NOTIFICATION_PREFERENCES_CHECK,
)


revision = "20260913_16"
down_revision = "20260913_15"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_users_notification_preferences_bounded"
DEFAULT_JSON = json.dumps(
    normalize_notification_preferences(None),
    ensure_ascii=True,
    separators=(",", ":"),
)
DEFAULT_SERVER_DEFAULT = sa.literal_column(f"'{DEFAULT_JSON}'")


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _columns() -> set[str]:
    return {
        item["name"] for item in inspect(op.get_bind()).get_columns("users")
    }


def _stored_preferences(value: object) -> dict[str, bool]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = None
    return normalize_notification_preferences(value)


def _sanitize_rows() -> None:
    users = sa.table(
        "users",
        sa.column("id", sa.BigInteger()),
        sa.column("notification_preferences", sa.JSON()),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(users.c.id, users.c.notification_preferences)
    ).mappings().all()
    if rows:
        bind.execute(
            sa.update(users)
            .where(users.c.id == sa.bindparam("user_key"))
            .values(notification_preferences=sa.bindparam("preferences")),
            [
                {
                    "user_key": row["id"],
                    "preferences": _stored_preferences(
                        row["notification_preferences"]
                    ),
                }
                for row in rows
            ],
        )


def upgrade() -> None:
    if "users" not in _tables():
        return
    if "notification_preferences" not in _columns():
        op.add_column(
            "users",
            sa.Column("notification_preferences", sa.JSON(), nullable=True),
        )
    _sanitize_rows()
    check_sql = (
        POSTGRESQL_NOTIFICATION_PREFERENCES_CHECK
        if op.get_bind().dialect.name == "postgresql"
        else SQLITE_NOTIFICATION_PREFERENCES_CHECK
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "notification_preferences",
            existing_type=sa.JSON(),
            nullable=False,
            server_default=DEFAULT_SERVER_DEFAULT,
        )
        batch_op.create_check_constraint(CONSTRAINT_NAME, check_sql)


def downgrade() -> None:
    if "users" not in _tables() or "notification_preferences" not in _columns():
        return
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
        batch_op.drop_column("notification_preferences")
