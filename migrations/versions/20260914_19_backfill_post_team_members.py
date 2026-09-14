"""Backfill post teams, owners, and already accepted applicants.

Revision ID: 20260914_19
Revises: 20260914_18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260914_19"
down_revision = "20260914_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {"posts", "teams", "team_members"} <= tables:
        return

    op.execute(sa.text("""
        INSERT INTO teams (
            post_id, owner_id, activity_name, division_of_labor,
            meeting_agenda, task_list, risk_reminders, contact_info, status
        )
        SELECT p.id, p.author_id, p.activity_name, '[]', '[]', '[]', '[]', '[]', 'active'
        FROM posts p
        WHERE p.join_mode <> 'none'
          AND NOT EXISTS (SELECT 1 FROM teams t WHERE t.post_id = p.id)
    """))
    op.execute(sa.text("""
        INSERT INTO team_members (team_id, user_id, suggested_role, member_role)
        SELECT t.id, p.author_id, '队长', 'owner'
        FROM teams t JOIN posts p ON p.id = t.post_id
        WHERE NOT EXISTS (
            SELECT 1 FROM team_members tm
            WHERE tm.team_id = t.id AND tm.user_id = p.author_id
        )
    """))
    if "applications" in tables:
        op.execute(sa.text("""
            INSERT INTO team_members (team_id, user_id, suggested_role, member_role)
            SELECT t.id, a.applicant_id, a.role_wanted, 'member'
            FROM applications a JOIN teams t ON t.post_id = a.post_id
            WHERE a.status = 'accepted'
              AND NOT EXISTS (
                  SELECT 1 FROM team_members tm
                  WHERE tm.team_id = t.id AND tm.user_id = a.applicant_id
              )
        """))
    op.execute(sa.text("""
        UPDATE posts
        SET current_members = (
            SELECT COUNT(DISTINCT tm.user_id)
            FROM teams t JOIN team_members tm ON tm.team_id = t.id
            WHERE t.post_id = posts.id
        )
        WHERE EXISTS (SELECT 1 FROM teams t WHERE t.post_id = posts.id)
    """))
    op.execute(sa.text("""
        UPDATE posts SET status = 'full'
        WHERE status = 'recruiting' AND current_members >= target_members
    """))


def downgrade() -> None:
    # Team membership is durable user data and must not be removed on downgrade.
    pass
