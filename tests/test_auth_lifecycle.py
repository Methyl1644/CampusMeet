from __future__ import annotations

import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import common
from api.schemas.auth import AccountDeactivateRequest
from services import auth_lifecycle
from storage.database.models import AccountRequest, AuthSession, User, VerificationCode
from storage.database.shared.model import Base
from utils.auth import hash_password, verify_password, verify_token


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            User(
                id=1,
                email="student@smail.nju.edu.cn",
                password_hash=hash_password("OldPassword2026"),
                nickname="student",
                auth_status="verified",
            )
        )
        session.commit()
    return factory


def test_issued_token_requires_an_active_server_session(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(common, "get_session", factory)
    with factory() as session:
        token = auth_lifecycle.issue_access_token(session, 1, ttl_seconds=3600)
        session.commit()
        payload = verify_token(token)
        assert payload and payload["jti"]

    assert common.current_user_id(f"Bearer {token}") == "1"

    with factory() as session:
        auth_lifecycle.revoke_session(session, payload["jti"], reason="logout")
        session.commit()
    with pytest.raises(HTTPException) as exc:
        common.current_user_id(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_password_change_revokes_every_existing_session():
    factory = _factory()
    with factory() as session:
        first = auth_lifecycle.issue_access_token(session, 1, ttl_seconds=3600)
        second = auth_lifecycle.issue_access_token(session, 1, ttl_seconds=3600)
        user = session.get(User, 1)
        auth_lifecycle.change_password(
            session,
            user,
            current_password="OldPassword2026",
            new_password="NewPassword2026",
        )
        session.commit()

        assert verify_password("NewPassword2026", user.password_hash)
        assert session.query(AuthSession).filter(AuthSession.revoked_at.is_(None)).count() == 0
        assert verify_token(first) and verify_token(second)


def test_account_requests_are_idempotent_and_deletion_deactivates_account():
    factory = _factory()
    with factory() as session:
        auth_lifecycle.issue_access_token(session, 1, ttl_seconds=3600)
        user = session.get(User, 1)
        first = auth_lifecycle.create_account_request(session, user, "data_export")
        repeated = auth_lifecycle.create_account_request(session, user, "data_export")
        deletion = auth_lifecycle.create_account_request(session, user, "account_deletion")
        session.commit()

        assert first.id == repeated.id
        assert deletion.request_type == "account_deletion"
        assert user.account_status == "deletion_requested"
        assert user.deactivated_at is not None
        assert session.query(AuthSession).filter(AuthSession.revoked_at.is_(None)).count() == 0
        assert session.query(AccountRequest).count() == 2


def test_expired_server_session_is_rejected_even_when_signature_is_valid(monkeypatch):
    factory = _factory()
    monkeypatch.setattr(common, "get_session", factory)
    with factory() as session:
        token = auth_lifecycle.issue_access_token(session, 1, ttl_seconds=3600)
        payload = verify_token(token)
        auth_session = session.get(AuthSession, payload["jti"])
        auth_session.expires_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)
        session.commit()

    with pytest.raises(HTTPException):
        common.current_user_id(f"Bearer {token}")


def test_account_deactivation_requires_only_the_current_password():
    request = AccountDeactivateRequest(current_password="OldPassword2026")

    assert request.current_password == "OldPassword2026"


def test_matching_verification_code_is_claimed_before_business_logic_finishes():
    from tools.auth_tools import _verify_code

    factory = _factory()
    with factory() as session:
        session.add(
            VerificationCode(
                account="student@smail.nju.edu.cn",
                code="123456",
                purpose="reset_password",
                expires_at=datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(minutes=10),
            )
        )
        session.commit()

    with factory() as first_session:
        claimed = _verify_code(
            first_session,
            "student@smail.nju.edu.cn",
            "reset_password",
            "123456",
        )
        assert claimed is not None
        assert claimed.used is True
        first_session.commit()

    with factory() as second_session:
        assert (
            _verify_code(
                second_session,
                "student@smail.nju.edu.cn",
                "reset_password",
                "123456",
            )
            is None
        )
