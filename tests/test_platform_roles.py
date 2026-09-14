from __future__ import annotations

import datetime
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api import operators as operators_api
from api.schemas.operators import PlatformRoleAcceptRequest
from services.operators import has_platform_role, require_senior_operator
from storage.database.models import AuditLog, PlatformRoleGrant, User
from storage.database.shared.model import Base


def _user(email: str, *, site_role: str = "student") -> User:
    return User(
        email=email,
        password_hash="hash",
        nickname=email.split("@", 1)[0],
        auth_status="verified",
        site_role=site_role,
    )


def _factory(*, users: list[User] | None = None):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add_all(
            users
            or [
                _user("senior@nju.edu.cn"),
                _user("operator@nju.edu.cn"),
                _user("target@nju.edu.cn"),
                _user("owner@nju.edu.cn"),
            ]
        )
        session.commit()
    return factory


def _grant(
    factory,
    *,
    user_id: int,
    role: str,
    granted_by: int | None = None,
    status: str = "active",
) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    with factory() as session:
        grant = PlatformRoleGrant(
            user_id=user_id,
            role=role,
            status=status,
            granted_by=granted_by or user_id,
            accepted_at=now if status == "active" else None,
            effective_at=now if status == "active" else None,
        )
        session.add(grant)
        session.commit()
        return grant.id


def _audit_actions(factory) -> list[str]:
    with factory() as session:
        return list(session.execute(select(AuditLog.action).order_by(AuditLog.id)).scalars())


def test_bootstrap_email_materializes_only_the_first_senior_operator(monkeypatch):
    factory = _factory(
        users=[
            _user("bootstrap@nju.edu.cn", site_role="operator"),
            _user("other-legacy@nju.edu.cn", site_role="operator"),
            _user("target@nju.edu.cn"),
        ]
    )
    monkeypatch.setattr(operators_api, "get_session", factory)
    monkeypatch.setenv("BOOTSTRAP_OPERATOR_EMAIL", "bootstrap@nju.edu.cn")

    invited = operators_api.invite_platform_role(
        {"user_id": 3, "role": "operator"}, "1"
    )

    assert invited["data"]["status"] == "pending"
    with factory() as session:
        grants = session.execute(
            select(PlatformRoleGrant).order_by(PlatformRoleGrant.id)
        ).scalars().all()
        assert [(grant.user_id, grant.role, grant.status) for grant in grants] == [
            (1, "senior_operator", "active"),
            (3, "operator", "pending"),
        ]

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 2, "role": "operator"}, "2"
        )
    assert exc.value.status_code == 403
    assert _audit_actions(factory) == ["platform_role.bootstrap", "platform_role.invite"]


def test_each_configured_staff_email_has_senior_operator_capability(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=2, role="operator", granted_by=1)
    monkeypatch.setenv("STAFF_EMAILS", "senior@nju.edu.cn, target@nju.edu.cn")

    with factory() as session:
        first = session.get(User, 1)
        third = session.get(User, 3)
        assert has_platform_role(session, first)
        assert has_platform_role(session, third)
        assert require_senior_operator(session, third).role == "senior_operator"


def test_only_active_senior_operator_can_invite_supported_roles(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=1, role="senior_operator")
    _grant(factory, user_id=2, role="operator", granted_by=1)
    monkeypatch.setattr(operators_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 3, "role": "operator"}, "2"
        )
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 3, "role": "owner"}, "1"
        )
    assert exc.value.status_code == 400

    result = operators_api.invite_platform_role(
        {"user_id": 3, "role": "senior_operator"}, "1"
    )
    assert result["data"]["role"] == "senior_operator"


def test_normal_organization_owner_has_no_platform_role_management_permission(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=1, role="senior_operator")
    monkeypatch.setattr(operators_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 3, "role": "operator"}, "4"
        )

    assert exc.value.status_code == 403


def test_invitation_must_be_accepted_by_target_after_recent_reauthentication(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=1, role="senior_operator")
    monkeypatch.setattr(operators_api, "get_session", factory)
    monkeypatch.setattr(operators_api, "verify_password", lambda password, _stored: password == "correct-password")
    grant_id = int(
        operators_api.invite_platform_role(
            {"user_id": 3, "role": "operator"}, "1"
        )["data"]["grant_id"]
    )

    with pytest.raises(HTTPException) as exc:
        operators_api.accept_platform_role(
            grant_id, PlatformRoleAcceptRequest(password="wrong-password"), "3"
        )
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        operators_api.accept_platform_role(
            grant_id, PlatformRoleAcceptRequest(password="correct-password"), "2"
        )
    assert exc.value.status_code == 403

    accepted = operators_api.accept_platform_role(
        grant_id, PlatformRoleAcceptRequest(password="correct-password"), "3"
    )
    assert accepted["data"]["status"] == "active"
    with factory() as session:
        grant = session.get(PlatformRoleGrant, grant_id)
        assert grant.accepted_at is not None
        assert grant.effective_at is not None
        assert grant.revoked_at is None
    assert _audit_actions(factory)[-1] == "platform_role.accept"


def test_senior_operator_cannot_invite_self_or_accept_a_self_issued_grant(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=1, role="senior_operator")
    monkeypatch.setattr(operators_api, "get_session", factory)
    monkeypatch.setattr(operators_api, "verify_password", lambda *_args: True)

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 1, "role": "operator"}, "1"
        )
    assert exc.value.status_code == 403

    self_grant_id = _grant(
        factory,
        user_id=3,
        role="operator",
        granted_by=3,
        status="pending",
    )
    with pytest.raises(HTTPException) as exc:
        operators_api.accept_platform_role(
            self_grant_id, PlatformRoleAcceptRequest(password="correct-password"), "3"
        )
    assert exc.value.status_code == 403


def test_suspend_and_revoke_are_audited_and_inactive_grants_no_longer_authorize(monkeypatch):
    factory = _factory()
    senior_id = _grant(factory, user_id=1, role="senior_operator")
    operator_id = _grant(factory, user_id=2, role="operator", granted_by=1)
    monkeypatch.setattr(operators_api, "get_session", factory)

    suspended = operators_api.suspend_platform_role(
        operator_id, {"reason": "security review"}, "1"
    )
    assert suspended["data"]["status"] == "suspended"

    with pytest.raises(HTTPException) as exc:
        operators_api.invite_platform_role(
            {"user_id": 3, "role": "operator"}, "2"
        )
    assert exc.value.status_code == 403

    second_senior_id = _grant(factory, user_id=3, role="senior_operator", granted_by=1)
    revoked = operators_api.revoke_platform_role(
        second_senior_id, {"reason": "left team"}, "1"
    )
    assert revoked["data"]["status"] == "revoked"

    with factory() as session:
        assert session.get(PlatformRoleGrant, operator_id).status == "suspended"
        assert session.get(PlatformRoleGrant, second_senior_id).revoked_at is not None
        assert session.get(PlatformRoleGrant, senior_id).status == "active"
        details = [
            json.loads(value)
            for value in session.execute(
                select(AuditLog.detail).where(
                    AuditLog.action.in_({"platform_role.suspend", "platform_role.revoke"})
                )
            ).scalars()
        ]
        assert [detail["reason"] for detail in details] == ["security review", "left team"]


def test_last_active_senior_operator_cannot_be_suspended_or_revoked(monkeypatch):
    factory = _factory()
    senior_id = _grant(factory, user_id=1, role="senior_operator")
    monkeypatch.setattr(operators_api, "get_session", factory)

    with pytest.raises(HTTPException) as exc:
        operators_api.suspend_platform_role(senior_id, {"reason": "rotation"}, "1")
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        operators_api.revoke_platform_role(senior_id, {"reason": "rotation"}, "1")
    assert exc.value.status_code == 409

    with factory() as session:
        grant = session.get(PlatformRoleGrant, senior_id)
        assert grant.status == "active"
        assert session.execute(
            select(AuditLog).where(
                AuditLog.action.in_({"platform_role.suspend", "platform_role.revoke"})
            )
        ).first() is None


def test_role_lists_expose_pending_invites_to_target_and_management_queue(monkeypatch):
    factory = _factory()
    _grant(factory, user_id=1, role="senior_operator")
    pending_id = _grant(factory, user_id=3, role="operator", granted_by=1, status="pending")
    monkeypatch.setattr(operators_api, "get_session", factory)

    mine = operators_api.my_platform_roles(page=1, page_size=20, user_id="3")
    queue = operators_api.list_platform_roles(
        status="all", page=1, page_size=20, user_id="1"
    )

    assert mine["data"]["list"][0]["grant_id"] == str(pending_id)
    assert mine["data"]["total"] == 1
    assert queue["data"]["total"] == 2

    with pytest.raises(HTTPException) as exc:
        operators_api.list_platform_roles(
            status="all", page=1, page_size=20, user_id="3"
        )
    assert exc.value.status_code == 403
