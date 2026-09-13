from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException


SAFE_PRODUCTION_ENV = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgresql://user:password@example.test/campusmate",
    "JWT_SECRET": "a" * 48,
    "AUTH_TEST_MODE": "false",
    "CAMPUS_EMAIL_DOMAINS": "nju.edu.cn,smail.nju.edu.cn",
    "FRONTEND_ORIGINS": "https://campusmate.example.test",
    "BREVO_API_KEY": "secret",
    "BREVO_FROM_EMAIL": "noreply@example.test",
}


def test_local_environment_does_not_require_production_credentials():
    from utils.runtime import production_config_errors

    assert production_config_errors({}) == []


def test_production_environment_rejects_unsafe_defaults_and_missing_delivery():
    from utils.runtime import production_config_errors

    errors = production_config_errors(
        {
            "APP_ENV": "production",
            "DATABASE_URL": "sqlite:///campusmate.db",
            "JWT_SECRET": "campusmate_default_secret_2026",
            "AUTH_TEST_MODE": "true",
            "CAMPUS_EMAIL_DOMAINS": "",
            "FRONTEND_ORIGINS": "*",
        }
    )

    assert {error.split(":", 1)[0] for error in errors} == {
        "DATABASE_URL",
        "JWT_SECRET",
        "AUTH_TEST_MODE",
        "CAMPUS_EMAIL_DOMAINS",
        "FRONTEND_ORIGINS",
        "EMAIL_DELIVERY",
    }


def test_production_environment_accepts_explicit_safe_configuration():
    from utils.runtime import production_config_errors

    assert production_config_errors(SAFE_PRODUCTION_ENV) == []


def test_production_allowlist_mode_requires_at_least_one_email():
    from utils.runtime import production_config_errors

    environment = {
        **SAFE_PRODUCTION_ENV,
        "AUTH_ACCESS_MODE": "allowlist",
        "AUTH_ALLOWED_EMAILS": "  ,  ",
    }

    assert "AUTH_ALLOWED_EMAILS: allowlist mode requires at least one email" in production_config_errors(
        environment
    )


def test_production_rejects_unknown_auth_access_mode():
    from utils.runtime import production_config_errors

    environment = {**SAFE_PRODUCTION_ENV, "AUTH_ACCESS_MODE": "private"}

    assert "AUTH_ACCESS_MODE: must be public or allowlist" in production_config_errors(environment)


def test_ready_endpoint_fails_without_exposing_database_exception(monkeypatch):
    import main

    class BrokenEngine:
        def connect(self):
            raise RuntimeError("postgresql://user:private-password@host/database")

    for key, value in SAFE_PRODUCTION_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(main, "get_engine", lambda: BrokenEngine())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main.readiness_check())

    assert exc.value.status_code == 503
    assert "private-password" not in str(exc.value.detail)
    assert exc.value.detail == {"status": "not_ready", "checks": {"configuration": "ok", "database": "failed"}}
