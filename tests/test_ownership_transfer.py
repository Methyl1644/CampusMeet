from __future__ import annotations

import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import identity as identity_api
from api.schemas.identity import OwnershipTransferRequest
from storage.database.models import (
    Organization,
    OrganizationMember,
    OrganizationOwnershipTransfer,
    User,
)
from storage.database.shared.model import Base


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        owner = User(
            email="owner@nju.edu.cn",
            password_hash="hash",
            nickname="owner",
            auth_status="verified",
        )
        successor = User(
            email="successor@nju.edu.cn",
            password_hash="hash",
            nickname="successor",
            auth_status="verified",
        )
        session.add_all([owner, successor])
        session.flush()
        organization = Organization(
            name="NJU Robotics Club",
            org_type="student_org",
            verification_status="approved",
            expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365),
        )
        session.add(organization)
        session.flush()
        session.add_all(
            [
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                    expires_at=organization.expires_at,
                ),
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=successor.id,
                    role="publisher",
                    status="active",
                    expires_at=organization.expires_at,
                ),
            ]
        )
        session.commit()
    return factory


def test_successor_must_accept_before_owner_changes(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)

    created = identity_api.create_organization_ownership_transfer(
        1, OwnershipTransferRequest(target_user_id=2), "1"
    )
    transfer_id = int(created["data"]["transfer_id"])
    with factory() as session:
        owners = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == 1,
                OrganizationMember.role == "owner",
                OrganizationMember.status == "active",
            )
        ).scalars().all()
        assert [owner.user_id for owner in owners] == [1]

    completed = identity_api.accept_organization_ownership_transfer(transfer_id, "2")
    assert completed["data"]["status"] == "completed"
    with factory() as session:
        memberships = {
            member.user_id: member.role
            for member in session.execute(select(OrganizationMember)).scalars().all()
        }
        assert memberships == {1: "member", 2: "owner"}


def test_non_target_cannot_accept_transfer(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(identity_api, "get_session", factory)
    transfer_id = int(
        identity_api.create_organization_ownership_transfer(
            1, OwnershipTransferRequest(target_user_id=2), "1"
        )["data"]["transfer_id"]
    )

    with pytest.raises(HTTPException) as exc:
        identity_api.accept_organization_ownership_transfer(transfer_id, "1")
    assert exc.value.status_code == 403
    with factory() as session:
        assert session.get(OrganizationOwnershipTransfer, transfer_id).status == "pending"
