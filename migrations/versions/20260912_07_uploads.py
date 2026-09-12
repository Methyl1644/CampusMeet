"""Add secure upload records.

Revision ID: 20260912_07
Revises: 20260912_06
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260912_07"
down_revision: Union[str, Sequence[str], None] = "20260912_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "uploads" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "uploads",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False, unique=True),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("expected_size", sa.Integer(), nullable=False),
        sa.Column("actual_size", sa.Integer(), nullable=True),
        sa.Column("private", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attached_to_type", sa.Text(), nullable=True),
        sa.Column("attached_to_id", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
    )
    op.create_index("ix_uploads_owner_status_created", "uploads", ["owner_id", "status", "created_at"])
    op.create_index("ix_uploads_object_key", "uploads", ["object_key"], unique=True)


def downgrade() -> None:
    raise RuntimeError("Upload audit records are intentionally retained.")
