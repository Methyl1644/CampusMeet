from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from api.schemas.auth import PasswordResetRequest


ACCESS_DENIED_MESSAGE = "当前为内部测试阶段，该账号暂未获得访问权限"


@pytest.fixture
def allowlist_environment(monkeypatch):
    monkeypatch.setenv("AUTH_ACCESS_MODE", "allowlist")
    monkeypatch.setenv(
        "AUTH_ALLOWED_EMAILS",
        " First@SMAIL.NJU.EDU.CN,second@nju.edu.cn ",
    )


@pytest.mark.parametrize(
    ("tool_name", "payload", "failure_key"),
    [
        (
            "register_auth_send_code",
            {"account": "blocked@smail.nju.edu.cn", "purpose": "register"},
            "sent",
        ),
        (
            "register_user",
            {
                "account": "blocked@smail.nju.edu.cn",
                "code": "123456",
                "password": "Password2026",
            },
            "success",
        ),
        (
            "login_user",
            {"account": "blocked@smail.nju.edu.cn", "password": "Password2026"},
            "success",
        ),
        (
            "verify_campus_email",
            {"user_id": "1", "email": "blocked@smail.nju.edu.cn", "code": "123456"},
            "verified",
        ),
    ],
)
def test_auth_tools_reject_unlisted_email_before_database_access(
    monkeypatch,
    allowlist_environment,
    tool_name,
    payload,
    failure_key,
):
    import tools.auth_tools as auth_tools

    monkeypatch.setattr(
        auth_tools,
        "get_session",
        lambda: pytest.fail("unlisted accounts must be rejected before database access"),
    )

    result = json.loads(getattr(auth_tools, tool_name).invoke(payload))

    assert result[failure_key] is False
    assert result["message"] == ACCESS_DENIED_MESSAGE


def test_auth_allowlist_normalizes_email_case_and_whitespace(
    allowlist_environment,
):
    from services.auth_access import auth_email_is_allowed

    assert auth_email_is_allowed("  FIRST@smail.nju.edu.cn ") is True


def test_allowlist_mode_with_empty_list_fails_closed_before_database_access(monkeypatch):
    import tools.auth_tools as auth_tools

    monkeypatch.setenv("AUTH_ACCESS_MODE", "allowlist")
    monkeypatch.setenv("AUTH_ALLOWED_EMAILS", "")
    monkeypatch.setattr(
        auth_tools,
        "get_session",
        lambda: pytest.fail("empty allowlist must fail closed"),
    )

    result = json.loads(
        auth_tools.login_user.invoke(
            {"account": "developer@smail.nju.edu.cn", "password": "Password2026"}
        )
    )

    assert result == {"success": False, "message": ACCESS_DENIED_MESSAGE}


def test_reset_password_rejects_unlisted_email_before_database_access(
    monkeypatch,
    allowlist_environment,
):
    from api import auth

    monkeypatch.setattr(
        auth,
        "get_session",
        lambda: pytest.fail("unlisted reset requests must not query the database"),
    )

    with pytest.raises(HTTPException) as exc:
        auth.reset_account_password(
            PasswordResetRequest(
                account="blocked@smail.nju.edu.cn",
                code="123456",
                new_password="Password2026",
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == ACCESS_DENIED_MESSAGE
