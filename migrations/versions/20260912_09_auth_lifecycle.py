"""Add revocable auth sessions and account request lifecycle.

Revision ID: 20260912_09
Revises: 20260912_08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260912_09"
down_revision: Union[str, Sequence[str], None] = "20260912_08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "account_status" not in user_columns:
        op.add_column(
            "users",
            sa.Column("account_status", sa.Text(), nullable=False, server_default="active"),
        )
    if "deactivated_at" not in user_columns:
        op.add_column("users", sa.Column("deactivated_at", sa.DateTime(timezone=True)))

    if "auth_sessions" not in tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Text(), primary_key=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
            sa.Column("revoke_reason", sa.Text()),
            sa.Column("last_seen_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at", "expires_at"])

    if "account_requests" not in tables:
        id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
        op.create_table(
            "account_requests",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("request_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("result_metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("cancelled_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index(
            "uq_pending_account_request",
            "account_requests",
            ["user_id", "request_type"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
            sqlite_where=sa.text("status = 'pending'"),
        )
        op.create_index("ix_account_requests_user_created", "account_requests", ["user_id", "created_at"])


def downgrade() -> None:
    raise RuntimeError("Authentication audit history is intentionally retained.")
