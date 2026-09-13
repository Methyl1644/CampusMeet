"""Idempotent post creation.

Revision ID: 20260913_17
Revises: 20260913_16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260913_17"
down_revision = "20260913_16"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "client_request_id" not in {column["name"] for column in inspector.get_columns("posts")}:
        op.add_column("posts", sa.Column("client_request_id", sa.Text(), nullable=True))
    if "uq_posts_author_request" not in {index["name"] for index in inspector.get_indexes("posts")}:
        op.create_index("uq_posts_author_request", "posts", ["author_id", "client_request_id"], unique=True)


def downgrade():
    op.drop_index("uq_posts_author_request", table_name="posts")
    with op.batch_alter_table("posts") as batch:
        batch.drop_column("client_request_id")
