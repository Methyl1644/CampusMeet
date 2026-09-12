import importlib
import json


def test_database_defaults_to_workspace_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PGDATABASE_URL", raising=False)

    import storage.database.db as db

    importlib.reload(db)

    assert db.get_db_url().startswith("sqlite:///")


def _fresh_sqlite_database(monkeypatch, tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'campusmate-test.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "test")

    import storage.database.db as db

    db._engine = None
    db._SessionLocal = None
    importlib.reload(db)

    from storage.database import models  # noqa: F401
    from storage.database.shared.model import Base

    Base.metadata.create_all(db.get_engine())
    return db


def test_student_email_code_can_be_sent_with_local_sqlite(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    first = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )

    assert first["sent"] is True
    assert first["test_mode"] is True
    assert first["code"].isdigit()
    assert len(first["code"]) == 6
    assert first["retry_after_seconds"] > 0


def test_repeated_campus_email_code_request_reuses_active_code(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    first = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )
    second = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )

    assert second["sent"] is True
    assert second["reused"] is True
    assert second["code"] == first["code"]
    assert "过于频繁" not in second["message"]


def test_login_code_cannot_be_used_to_register(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    login_code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "login"}
        )
    )["code"]
    result = json.loads(
        auth_tools.register_user.invoke(
            {
                "account": "student@smail.nju.edu.cn",
                "code": login_code,
                "password": "TestPassword2026",
                "nickname": "测试用户",
                "major": "计算机",
                "grade": "大一",
                "skills": "Python",
            }
        )
    )

    assert result["success"] is False
    assert result["message"] == "验证码无效或已过期"


def test_registered_user_can_login_with_a_login_code(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "teacher@nju.edu.cn"
    register_code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "register"}
        )
    )["code"]
    registered = json.loads(
        auth_tools.register_user.invoke(
            {
                "account": account,
                "code": register_code,
                "password": "TestPassword2026",
                "nickname": "测试用户",
                "major": "计算机",
                "grade": "大一",
                "skills": "Python",
            }
        )
    )
    assert registered["success"] is True

    login_code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "login"}
        )
    )["code"]
    logged_in = json.loads(
        auth_tools.login_user.invoke(
            {"account": account, "password": "", "code": login_code}
        )
    )

    assert logged_in["success"] is True
    assert logged_in["user"]["email"] == account
    assert logged_in["token"]


def test_password_login_is_temporarily_locked_after_repeated_failures(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "student@smail.nju.edu.cn"
    register_code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "register"}
        )
    )["code"]
    auth_tools.register_user.invoke(
        {
            "account": account,
            "code": register_code,
            "password": "TestPassword2026",
            "nickname": "测试用户",
            "major": "计算机",
            "grade": "大一",
            "skills": "Python",
        }
    )

    for _ in range(auth_tools.MAX_PASSWORD_ATTEMPTS):
        failed = json.loads(
            auth_tools.login_user.invoke(
                {"account": account, "password": "WrongPassword2026", "code": ""}
            )
        )
        assert failed["success"] is False

    locked = json.loads(
        auth_tools.login_user.invoke(
            {"account": account, "password": "TestPassword2026", "code": ""}
        )
    )
    assert locked == {"success": False, "message": "登录尝试过多，请稍后再试"}


def test_registration_requires_a_real_password(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "student@smail.nju.edu.cn"
    code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "register"}
        )
    )["code"]
    result = json.loads(
        auth_tools.register_user.invoke(
            {
                "account": account,
                "code": code,
                "password": "",
                "nickname": "测试用户",
                "major": "计算机",
                "grade": "大一",
                "skills": "Python",
            }
        )
    )

    assert result == {
        "success": False,
        "message": "密码至少 8 位，并同时包含字母和数字",
    }


def test_production_email_failure_does_not_leak_the_code(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setenv("AUTH_TEST_MODE", "false")
    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    monkeypatch.setattr(
        auth_tools,
        "send_verification_email",
        lambda *_: {
            "sent": True,
            "code": "123456",
            "message": "邮件发送失败，验证码为: 123456",
        },
    )

    result = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )

    assert result["sent"] is False
    assert "code" not in result
    assert "123456" not in result["message"]


def test_production_verification_code_is_hashed_at_rest(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools
    from storage.database.models import VerificationCode

    monkeypatch.setenv("AUTH_TEST_MODE", "false")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    monkeypatch.setattr(
        auth_tools,
        "generate_verification_code",
        lambda: "654321",
    )
    monkeypatch.setattr(
        auth_tools,
        "send_verification_email",
        lambda *_: {"sent": True, "message": "sent"},
    )

    result = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )
    with db.get_session() as session:
        stored = session.query(VerificationCode).one()

    assert result["sent"] is True
    assert "code" not in result
    assert stored.code.startswith("sha256$")
    assert "654321" not in stored.code


def test_verification_code_expires_after_repeated_wrong_attempts(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "student@smail.nju.edu.cn"
    code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "register"}
        )
    )["code"]
    payload = {
        "account": account,
        "password": "TestPassword2026",
        "nickname": "测试用户",
        "major": "计算机",
        "grade": "大一",
        "skills": "Python",
    }
    for _ in range(auth_tools.MAX_CODE_ATTEMPTS):
        result = json.loads(auth_tools.register_user.invoke({**payload, "code": "000000"}))
        assert result["success"] is False

    result = json.loads(auth_tools.register_user.invoke({**payload, "code": code}))
    assert result["success"] is False
    assert result["message"] == "验证码无效或已过期"


def test_failed_email_delivery_does_not_block_an_immediate_retry(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    calls = []
    monkeypatch.setenv("AUTH_TEST_MODE", "false")
    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    monkeypatch.setattr(
        auth_tools,
        "send_verification_email",
        lambda *_: calls.append("attempt")
        or {"sent": False, "message": "验证码邮件发送失败，请稍后重试"},
    )

    first = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )
    second = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@smail.nju.edu.cn", "purpose": "register"}
        )
    )

    assert first["sent"] is False
    assert second["sent"] is False
    assert calls == ["attempt", "attempt"]
    assert second.get("reused") is not True


def test_campus_verification_code_rejects_non_campus_email(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    result = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": "student@example.com", "purpose": "campus_verify"}
        )
    )

    assert result == {
        "sent": False,
        "message": "请使用南京大学校园邮箱完成认证",
    }


def test_campus_email_domain_accepts_only_student_and_staff_mail_domains(
    monkeypatch,
):
    import tools.auth_tools as auth_tools

    monkeypatch.delenv("CAMPUS_EMAIL_DOMAINS", raising=False)

    assert auth_tools._is_campus_email("student@nju.edu.cn") is True
    assert auth_tools._is_campus_email("student@smail.nju.edu.cn") is True
    assert auth_tools._is_campus_email("student@math.nju.edu.cn") is False
    assert auth_tools._is_campus_email("student@evilnju.edu.cn") is False


def test_registration_code_rejects_phone_and_non_campus_email(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)

    for account in ("13800138000", "student@example.com"):
        result = json.loads(
            auth_tools.register_auth_send_code.invoke(
                {"account": account, "purpose": "register"}
            )
        )
        assert result == {
            "sent": False,
            "message": "仅支持南京大学校园邮箱注册",
        }


def test_campus_registration_is_verified_immediately(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    account = "student@smail.nju.edu.cn"
    code = json.loads(
        auth_tools.register_auth_send_code.invoke(
            {"account": account, "purpose": "register"}
        )
    )["code"]
    result = json.loads(
        auth_tools.register_user.invoke(
            {
                "account": account,
                "code": code,
                "password": "TestPassword2026",
                "nickname": "测试用户",
                "major": "计算机",
                "grade": "大一",
                "skills": "Python",
            }
        )
    )

    assert result["success"] is True
    assert result["user"]["auth_status"] == "verified"
    assert result["user"]["verified_email"] == account
    assert result["message"] == "注册成功"


def test_registration_rejects_non_campus_account_before_code_validation(
    monkeypatch, tmp_path
):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import tools.auth_tools as auth_tools

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    result = json.loads(
        auth_tools.register_user.invoke(
            {
                "account": "outsider@example.com",
                "code": "123456",
                "password": "TestPassword2026",
                "nickname": "测试用户",
                "major": "计算机",
                "grade": "大一",
                "skills": "Python",
            }
        )
    )

    assert result == {
        "success": False,
        "message": "仅支持南京大学校园邮箱注册",
    }


def test_campus_email_cannot_verify_more_than_one_account(monkeypatch, tmp_path):
    db = _fresh_sqlite_database(monkeypatch, tmp_path)

    import datetime
    import tools.auth_tools as auth_tools
    from storage.database.models.user import User
    from storage.database.models.verification_code import VerificationCode

    campus_email = "shared@smail.nju.edu.cn"
    session = db.get_session()
    first_user = User(
        email="first@example.com",
        password_hash="hash",
        nickname="first",
        verified_email=campus_email,
        auth_status="verified",
    )
    second_user = User(
        email="second@example.com",
        password_hash="hash",
        nickname="second",
    )
    session.add_all([first_user, second_user])
    session.flush()
    second_user_id = second_user.id
    session.add(
        VerificationCode(
            account=campus_email,
            code="123456",
            purpose="campus_verify",
            expires_at=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=10),
        )
    )
    session.commit()
    session.close()

    monkeypatch.setattr(auth_tools, "get_session", db.get_session)
    result = json.loads(
        auth_tools.verify_campus_email.invoke(
            {
                "user_id": str(second_user_id),
                "email": campus_email,
                "code": "123456",
            }
        )
    )

    assert result == {
        "verified": False,
        "message": "该校园邮箱已绑定其他账号",
    }
