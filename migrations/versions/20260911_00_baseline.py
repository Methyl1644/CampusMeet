"""Adopt the current CampusMate schema without recreating production tables.

Revision ID: 20260911_00
Revises: None
Create Date: 2026-09-11
"""
from typing import Sequence, Union

from alembic import op

from storage.database.models import *  # noqa: F403 - registers model metadata
from storage.database.shared.model import Base


revision: str = "20260911_00"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing Render/Neon databases already contain these tables. checkfirst
    # lets the first migration adopt them while still supporting a fresh DB.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # The baseline may have adopted pre-existing production tables. Never
    # destroy those tables when removing only Alembic's version marker.
    pass
