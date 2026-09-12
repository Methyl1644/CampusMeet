from __future__ import annotations

from sqlalchemy import create_engine, inspect

from storage.database.models import (
    OrganizationApplication,
    OrganizationInvitation,
    OrganizationOwnershipTransfer,
    PlatformRoleGrant,
)
from storage.database.shared.model import Base


def _foreign_keys(table) -> set[tuple[str, str, str]]:
    return {
        (element.parent.name, constraint.referred_table.name, element.column.name)
        for constraint in table.foreign_key_constraints
        for element in constraint.elements
    }


def test_organization_application_has_structured_verification_fields() -> None:
    columns = set(OrganizationApplication.__table__.columns.keys())

    assert {
        "school_scope",
        "official_page",
        "responsible_person_statement",
        "evidence_reference",
        "review_reason",
        "expires_at",
    } <= columns


def test_identity_models_declare_required_fields_and_foreign_keys() -> None:
    invitation_columns = set(OrganizationInvitation.__table__.columns.keys())
    assert {
        "organization_id",
        "inviter_id",
        "invitee_id",
        "requested_role",
        "token_hash",
        "status",
        "expires_at",
        "accepted_at",
        "revoked_at",
        "created_at",
    } <= invitation_columns
    assert {
        ("organization_id", "organizations", "id"),
        ("inviter_id", "users", "id"),
        ("invitee_id", "users", "id"),
    } <= _foreign_keys(OrganizationInvitation.__table__)

    grant_columns = set(PlatformRoleGrant.__table__.columns.keys())
    assert {
        "user_id",
        "role",
        "status",
        "granted_by",
        "accepted_at",
        "effective_at",
        "expires_at",
        "revoked_at",
        "created_at",
    } <= grant_columns
    assert {
        ("user_id", "users", "id"),
        ("granted_by", "users", "id"),
    } <= _foreign_keys(PlatformRoleGrant.__table__)

    transfer_columns = set(OrganizationOwnershipTransfer.__table__.columns.keys())
    assert {
        "organization_id",
        "from_owner_id",
        "to_owner_id",
        "initiated_by",
        "status",
        "expires_at",
        "accepted_at",
        "completed_at",
        "revoked_at",
        "created_at",
    } <= transfer_columns
    assert {
        ("organization_id", "organizations", "id"),
        ("from_owner_id", "users", "id"),
        ("to_owner_id", "users", "id"),
        ("initiated_by", "users", "id"),
    } <= _foreign_keys(OrganizationOwnershipTransfer.__table__)


def test_identity_tables_expose_retry_and_lookup_indexes(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'identity.db'}")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    invitation_indexes = {item["name"]: item for item in inspector.get_indexes("organization_invitations")}
    assert invitation_indexes["uq_pending_organization_invitation"]["unique"] == 1
    assert "ix_organization_invitations_invitee_status" in invitation_indexes

    role_indexes = {item["name"]: item for item in inspector.get_indexes("platform_role_grants")}
    assert role_indexes["uq_current_platform_role_grant"]["unique"] == 1
    assert "ix_platform_role_grants_user_status" in role_indexes

    transfer_indexes = {
        item["name"]: item for item in inspector.get_indexes("organization_ownership_transfers")
    }
    assert transfer_indexes["uq_pending_organization_ownership_transfer"]["unique"] == 1
    assert "ix_organization_ownership_transfers_target_status" in transfer_indexes
