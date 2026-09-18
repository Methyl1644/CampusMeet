"""Track the storage provider and verified Cloudinary metadata per upload.

Revision ID: 20260914_20
Revises: 20260914_19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260914_20"
down_revision: Union[str, Sequence[str], None] = "20260914_19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CLOUDINARY_COLUMNS = (
    ("cloudinary_asset_id", sa.Text()),
    ("cloudinary_public_id", sa.Text()),
    ("cloudinary_resource_type", sa.Text()),
    ("cloudinary_delivery_type", sa.Text()),
    ("cloudinary_format", sa.Text()),
    ("cloudinary_version", sa.Integer()),
    ("cloudinary_secure_url", sa.Text()),
)


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "uploads" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("uploads")}

    if "provider" not in existing:
        # server_default backfills every pre-Cloudinary row as 's3'.
        op.add_column(
            "uploads",
            sa.Column("provider", sa.Text(), nullable=False, server_default="s3"),
        )

    for name, column_type in CLOUDINARY_COLUMNS:
        if name not in existing:
            op.add_column("uploads", sa.Column(name, column_type, nullable=True))

    index_names = {index["name"] for index in inspector.get_indexes("uploads")}
    if "ix_uploads_cloudinary_public_id" not in index_names:
        op.create_index(
            "ix_uploads_cloudinary_public_id",
            "uploads",
            ["cloudinary_public_id"],
            unique=True,
        )


def downgrade() -> None:
    raise RuntimeError("Upload audit records are intentionally retained.")
