"""Add official identity governance records and verification fields.

Revision ID: 20260911_02
Revises: 20260911_01
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260911_02"
down_revision: Union[str, Sequence[str], None] = "20260911_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_COLUMN_TYPES = (
    ("school_scope", sa.Text),
    ("official_page", sa.Text),
    ("responsible_person_statement", sa.Text),
    ("evidence_reference", sa.Text),
    ("review_reason", sa.Text),
    ("expires_at", lambda: sa.DateTime(timezone=True)),
)


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _index_names(table_name: str) -> set[str]:
    return {item["name"] for item in inspect(op.get_bind()).get_indexes(table_name)}


def _add_application_columns() -> None:
    existing = {item["name"] for item in inspect(op.get_bind()).get_columns("organization_applications")}
    for name, type_factory in APPLICATION_COLUMN_TYPES:
        if name not in existing:
            op.add_column("organization_applications", sa.Column(name, type_factory(), nullable=True))


def _create_identity_tables() -> None:
    tables = _tables()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

    if "organization_invitations" not in tables:
        op.create_table(
            "organization_invitations",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("organization_id", sa.BigInteger(), nullable=False),
            sa.Column("inviter_id", sa.BigInteger(), nullable=False),
            sa.Column("invitee_id", sa.BigInteger(), nullable=False),
            sa.Column("requested_role", sa.Text(), nullable=False),
            sa.Column("token_hash", sa.Text(), nullable=True),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["organization_id"], ["organizations.id"], name="fk_org_invitations_org", ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], name="fk_org_invitations_inviter"),
            sa.ForeignKeyConstraint(["invitee_id"], ["users.id"], name="fk_org_invitations_invitee"),
            sa.UniqueConstraint("token_hash", name="uq_organization_invitation_token_hash"),
        )

    if "platform_role_grants" not in tables:
        op.create_table(
            "platform_role_grants",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("role", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("granted_by", sa.BigInteger(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_platform_role_grants_user"),
            sa.ForeignKeyConstraint(["granted_by"], ["users.id"], name="fk_platform_role_grants_grantor"),
        )

    if "organization_ownership_transfers" not in tables:
        op.create_table(
            "organization_ownership_transfers",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("organization_id", sa.BigInteger(), nullable=False),
            sa.Column("from_owner_id", sa.BigInteger(), nullable=False),
            sa.Column("to_owner_id", sa.BigInteger(), nullable=False),
            sa.Column("initiated_by", sa.BigInteger(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name="fk_org_ownership_transfers_org",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["from_owner_id"], ["users.id"], name="fk_org_ownership_transfers_from_owner"
            ),
            sa.ForeignKeyConstraint(
                ["to_owner_id"], ["users.id"], name="fk_org_ownership_transfers_to_owner"
            ),
            sa.ForeignKeyConstraint(
                ["initiated_by"], ["users.id"], name="fk_org_ownership_transfers_initiator"
            ),
        )


def _assert_no_conflicting_legacy_rows() -> None:
    duplicate_application = op.get_bind().execute(
        sa.text(
            "SELECT applicant_id, organization_name FROM organization_applications "
            "WHERE status = 'pending' GROUP BY applicant_id, organization_name "
            "HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate_application:
        raise RuntimeError(
            "Cannot enforce identity governance while duplicate pending organization applications exist "
            f"for applicant_id={duplicate_application.applicant_id}, "
            f"organization_name={duplicate_application.organization_name!r}. No rows were deleted."
        )

    duplicate_owner = op.get_bind().execute(
        sa.text(
            "SELECT organization_id FROM organization_members "
            "WHERE role = 'owner' AND status = 'active' GROUP BY organization_id "
            "HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate_owner:
        raise RuntimeError(
            "Cannot enforce identity governance while multiple active owners exist "
            f"for organization_id={duplicate_owner.organization_id}. No rows were deleted."
        )


def _create_indexes() -> None:
    invitation_indexes = _index_names("organization_invitations")
    if "uq_pending_organization_invitation" not in invitation_indexes:
        op.create_index(
            "uq_pending_organization_invitation",
            "organization_invitations",
            ["organization_id", "invitee_id"],
            unique=True,
            sqlite_where=sa.text("status = 'pending' AND revoked_at IS NULL"),
            postgresql_where=sa.text("status = 'pending' AND revoked_at IS NULL"),
        )
    if "ix_organization_invitations_invitee_status" not in invitation_indexes:
        op.create_index(
            "ix_organization_invitations_invitee_status",
            "organization_invitations",
            ["invitee_id", "status"],
        )

    grant_indexes = _index_names("platform_role_grants")
    if "uq_current_platform_role_grant" not in grant_indexes:
        op.create_index(
            "uq_current_platform_role_grant",
            "platform_role_grants",
            ["user_id", "role"],
            unique=True,
            sqlite_where=sa.text("status IN ('pending', 'active') AND revoked_at IS NULL"),
            postgresql_where=sa.text("status IN ('pending', 'active') AND revoked_at IS NULL"),
        )
    if "ix_platform_role_grants_user_status" not in grant_indexes:
        op.create_index(
            "ix_platform_role_grants_user_status", "platform_role_grants", ["user_id", "status"]
        )

    transfer_indexes = _index_names("organization_ownership_transfers")
    if "uq_pending_organization_ownership_transfer" not in transfer_indexes:
        op.create_index(
            "uq_pending_organization_ownership_transfer",
            "organization_ownership_transfers",
            ["organization_id"],
            unique=True,
            sqlite_where=sa.text("status = 'pending' AND revoked_at IS NULL"),
            postgresql_where=sa.text("status = 'pending' AND revoked_at IS NULL"),
        )
    if "ix_organization_ownership_transfers_target_status" not in transfer_indexes:
        op.create_index(
            "ix_organization_ownership_transfers_target_status",
            "organization_ownership_transfers",
            ["to_owner_id", "status"],
        )

    application_indexes = _index_names("organization_applications")
    if "uq_pending_organization_application" not in application_indexes:
        op.create_index(
            "uq_pending_organization_application",
            "organization_applications",
            ["applicant_id", "organization_name"],
            unique=True,
            sqlite_where=sa.text("status = 'pending'"),
            postgresql_where=sa.text("status = 'pending'"),
        )

    member_indexes = _index_names("organization_members")
    if "uq_active_organization_owner" not in member_indexes:
        op.create_index(
            "uq_active_organization_owner",
            "organization_members",
            ["organization_id"],
            unique=True,
            sqlite_where=sa.text("role = 'owner' AND status = 'active'"),
            postgresql_where=sa.text("role = 'owner' AND status = 'active'"),
        )


def upgrade() -> None:
    tables = _tables()
    required = {"users", "organizations", "organization_members", "organization_applications"}
    missing = required - tables
    if missing:
        raise RuntimeError(f"Identity governance migration requires existing tables: {sorted(missing)}")

    _add_application_columns()
    _create_identity_tables()
    _assert_no_conflicting_legacy_rows()
    _create_indexes()


def downgrade() -> None:
    raise RuntimeError(
        "Identity governance migration is intentionally irreversible because dropping it would delete "
        "verification and role history."
    )
