import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import auth
from storage.database.models import AuthSession, User
from storage.database.shared.model import Base
from utils.auth import hash_password, verify_token


def _factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            User(
                id=1,
                email="reviewer@smail.nju.edu.cn",
                password_hash=hash_password("UnusedPassword2026"),
                nickname="游客账号",
                auth_status="verified",
                site_role="senior_operator",
                account_status="active",
                onboarding_completed_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        session.commit()
    return factory


def _enable(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-with-at-least-32-characters")
    monkeypatch.setenv("REVIEW_DEMO_ENABLED", "true")
    monkeypatch.setenv("REVIEW_DEMO_EMAIL", "reviewer@smail.nju.edu.cn")
    monkeypatch.setenv("REVIEW_DEMO_EXPIRES_AT", "2099-01-01T00:00:00Z")
    monkeypatch.setenv("AUTH_ACCESS_MODE", "allowlist")
    monkeypatch.setenv("AUTH_ALLOWED_EMAILS", "reviewer@smail.nju.edu.cn")
    monkeypatch.setenv("STAFF_EMAILS", "reviewer@smail.nju.edu.cn")


def test_quick_experience_is_hidden_when_disabled(monkeypatch):
    monkeypatch.delenv("REVIEW_DEMO_ENABLED", raising=False)
    assert auth.review_demo_status()["data"] == {"available": False}

    with pytest.raises(HTTPException) as exc:
        auth.quick_experience()
    assert exc.value.status_code == 404


def test_quick_experience_issues_short_lived_session_for_configured_staff(monkeypatch):
    factory = _factory()
    _enable(monkeypatch)
    monkeypatch.setattr(auth, "get_session", factory)

    response = auth.quick_experience()
    token = response["data"]["token"]
    payload = verify_token(token)

    assert response["data"]["user"]["nickname"] == "游客账号"
    assert payload and payload["user_id"] == 1
    assert payload["exp"] - payload["iat"] <= 7200
    with factory() as session:
        assert session.query(AuthSession).count() == 1


def test_quick_experience_refuses_an_unconfigured_or_expired_account(monkeypatch):
    factory = _factory()
    _enable(monkeypatch)
    monkeypatch.setattr(auth, "get_session", factory)
    monkeypatch.setenv("REVIEW_DEMO_EXPIRES_AT", "2020-01-01T00:00:00Z")

    assert auth.review_demo_status()["data"] == {"available": False}
    with pytest.raises(HTTPException) as exc:
        auth.quick_experience()
    assert exc.value.status_code == 404
